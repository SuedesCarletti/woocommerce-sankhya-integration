from flask import Flask, request, jsonify
import hmac
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# Importa o blueprint de webhooks (módulo completo)
from webhooks import webhook_bp
# --- FIX INÍCIO ---
from routes.nfe import nfe_bp
# --- FIX FIM ---

# Importa outros serviços
from services.woocommerce import WooCommerceService
from services.sankhya import SankhyaService
from config.settings import load_config
from utils import setup_logger

load_dotenv()
app = Flask(__name__)

# Carrega configurações
config = load_config(app)
logger = setup_logger("main-app", level="INFO")

# Registra o blueprint de webhooks
app.register_blueprint(webhook_bp, url_prefix='/webhook')

# --- FIX INÍCIO ---
# Registra o blueprint de NFe visualization (fix para erro 404)
app.register_blueprint(nfe_bp, url_prefix='/nfe')



# Configurações do WooCommerce para endpoints auxiliares
WC_URL = config.get("WC_URL")
WC_KEY = config.get("WC_KEY") 
WC_SECRET = config.get("WC_SECRET")
WEBHOOK_TOKEN = config.get("WEBHOOK_SECRET")


def token_valido(token):
    """Compara o token em tempo constante; recusa se o segredo não estiver configurado."""
    if not token or not WEBHOOK_TOKEN:
        return False
    return hmac.compare_digest(str(token), str(WEBHOOK_TOKEN))


def token_da_requisicao():
    """Aceita ?token= ou o header X-API-Token (o header evita token em log/URL)."""
    return request.args.get("token") or request.headers.get("X-API-Token")


@app.before_request
def exigir_token_nfe():
    """DANFE contém dados fiscais do cliente: nada de acesso anônimo por número de pedido."""
    if not request.path.startswith("/nfe/") or request.path.endswith("/health"):
        return None
    if not token_valido(token_da_requisicao()):
        return jsonify({"erro": "Token inválido"}), 401
    return None

# SUBSTITUA a função get_orders() no app.py por esta versão corrigida:

def get_orders():
    """Busca pedidos do WooCommerce - VERSÃO CORRIGIDA"""
    if not all([WC_URL, WC_KEY, WC_SECRET]):
        raise ValueError("Configurações do WooCommerce não encontradas")
    
    # CORREÇÃO: Remove barras finais da URL base
    base_url = WC_URL.rstrip('/')
    
    # CORREÇÃO: Constrói URL corretamente para API do WooCommerce
    # Se a URL base já contém /wp-json/wc/v3, usa diretamente
    if '/wp-json/wc/v3' in base_url:
        url = f"{base_url}/orders"
    else:
        # Caso contrário, adiciona o caminho da API
        url = f"{base_url}/wp-json/wc/v3/orders"
    
    print(f"[GET_ORDERS] URL construída: {url}")
    
    try:
        response = requests.get(url, auth=(WC_KEY, WC_SECRET), timeout=30)
        
        if response.status_code >= 400:
            print(f"[GET_ORDERS] Erro HTTP {response.status_code}")
            print(f"[GET_ORDERS] Response: {response.text[:200]}")
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"[GET_ORDERS] Erro na requisição: {e}")
        raise

# ALTERNATIVA: Use o WooCommerceService já corrigido
def get_orders_via_service():
    """Alternativa usando o serviço já corrigido"""
    try:
        woo_service = WooCommerceService()
        resultado = woo_service.buscar_pedidos(limit=10)
        
        if resultado['status'] == 'success':
            return resultado['pedidos']
        else:
            raise Exception(resultado.get('message', 'Erro desconhecido'))
            
    except Exception as e:
        print(f"[GET_ORDERS_SERVICE] Erro: {e}")
        raise

@app.before_request
def log_request_info():
    """Log de todas as requisições"""
    logger.info(f"{request.method} {request.path} - IP: {request.remote_addr}")

@app.after_request  
def log_response_info(response):
    """Log de todas as respostas"""
    if response.status_code >= 400:
        logger.error(f"{request.method} {request.path} - Status: {response.status_code}")
    else:
        logger.info(f"{request.method} {request.path} - Status: {response.status_code}")
    return response

@app.route("/", methods=["GET"])
def root():
    """Endpoint raiz com informações da API"""
    return jsonify({
        "message": "WooCommerce-Sankhya Integration API",
        "version": "2.2",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "new_features": [
            "Suporte a transportadoras",
            "Processamento de AllPost",
            "TIPMOV = P (Pedido)",
            "Informações de frete"
        ],
        "endpoints": [
            "GET  / - Esta página",
            "GET  /health - Health check geral",
            "GET  /version - Versões dos módulos",
            "GET  /config - Configurações (com token)",
            "",
            "=== WEBHOOKS ===",
            "POST /webhook/ - Webhook principal (WooCommerce)",
            "GET  /webhook/health - Health check dos webhooks", 
            "GET  /webhook/stats - Estatísticas (com token)",
            "POST /webhook/test - Teste de webhook (dev, com token)",
            "",
            "=== WOOCOMMERCE ===",
            "GET  /woo/orders - Listar pedidos (com token)",
            "",
            "=== SANKHYA ===",
            "GET  /sankhya/transportadoras - Listar transportadoras (com token)",
            "GET  /sankhya/stats - Estatísticas do sistema (com token)",
            "POST /sankhya/test - Teste de integração (com token)",
            "",
            "=== UTILITÁRIOS ===",
            "POST /sync/orders - Sincronização manual (com token)",
            "",
            "=== NFE/DANFE (VIEW) ===",
            "GET  /nfe/view/<id> - Visualização HTML da NFe"
        ]
    }), 200

@app.route("/customers/woocommerce", methods=["POST"])
def sync_customer_woocommerce():
    """
    Endpoint: Sincroniza cliente WooCommerce → Sankhya
    """
    if not token_valido(token_da_requisicao()):
        return jsonify({"erro": "Token inválido"}), 401

    try:
        data = request.get_json(silent=True) or {}
        customer_data = data.get('customer_data')
        
        if not customer_data:
            return jsonify({
                'erro': 'customer_data obrigatório'
            }), 400
        
        with SankhyaService.with_auth() as sankhya:
            resultado = sankhya.processar_cliente_completo(customer_data)
            
            # CORREÇÃO: Usa chave correta 'sucesso_geral'
            if resultado.get('sucesso_geral', False):
                return jsonify({
                    'sucesso': True,
                    'codparc': resultado.get('codparc_sankhya'),
                    'mensagem': 'Cliente processado com sucesso',
                    'detalhes': resultado
                }), 200
            else:
                return jsonify({
                    'sucesso': False,
                    'erros': resultado.get('erros', ['Erro desconhecido']),
                    'detalhes': resultado
                }), 400
                
    except Exception as e:
        logger.error(f"Erro na sincronização de cliente: {e}")
        return jsonify({
            'erro': f'Erro interno: {str(e)}'
        }), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check geral da aplicação"""
    try:
        # Verifica configurações essenciais
        checks = {
            'config_loaded': bool(config),
            'webhook_secret': bool(config.get('WEBHOOK_SECRET')),
            'woocommerce_configured': bool(WC_URL and WC_KEY and WC_SECRET),
            'sankhya_configured': bool(
                config.get('SANKHYA_BASE_URL') and 
                config.get('SANKHYA_APPKEY') and 
                config.get('SANKHYA_USERNAME')
            ),
            'environment': config.get('USAR_AMBIENTE', 'sandbox'),
            'transportadoras_support': True
        }
        
        all_ok = all(value for key, value in checks.items() if key not in ['environment', 'transportadoras_support'])
        
        return jsonify({
            "status": "healthy" if all_ok else "degraded",
            "service": "woocommerce-sankhya-integration",
            "version": "2.2",
            "environment": checks['environment'],
            "checks": checks,
            "new_features": ["transportadoras", "allpost_integration", "tipmov_P"],
            "timestamp": datetime.now().isoformat()
        }), 200 if all_ok else 503
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/version", methods=["GET"])
def version_info():
    """Informações de versão dos módulos"""
    try:
        versions = {}
        
        # Tenta importar e obter versões dos módulos
        try:
            from services import __version__ as services_version
            versions['services'] = services_version
        except:
            versions['services'] = 'unknown'
            
        try:
            from webhooks import __version__ as webhooks_version
            versions['webhooks'] = webhooks_version
        except:
            versions['webhooks'] = 'unknown'
            
        try:
            from utils import __version__ as utils_version
            versions['utils'] = utils_version
        except:
            versions['utils'] = 'unknown'
        
        return jsonify({
            "application": "2.2",
            "python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "modules": versions,
            "features": {
                "transportadoras": "2.2.0",
                "allpost_integration": "2.2.0"
            },
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/config", methods=["GET"])
def config_info():
    """Informações de configuração (requer token)"""
    token = token_da_requisicao()
    if not token_valido(token):
        return jsonify({"erro": "Token inválido"}), 401
    
    try:
        # Remove dados sensíveis
        safe_config = {
            'USAR_AMBIENTE': config.get('USAR_AMBIENTE'),
            'WC_URL': config.get('WC_URL'),
            'WC_KEY_CONFIGURED': bool(config.get('WC_KEY')),
            'WC_SECRET_CONFIGURED': bool(config.get('WC_SECRET')),
            'SANKHYA_BASE_URL': config.get('SANKHYA_BASE_URL'),
            'SANKHYA_USERNAME': config.get('SANKHYA_USERNAME'),
            'SANKHYA_APPKEY_CONFIGURED': bool(config.get('SANKHYA_APPKEY')),
            'SANKHYA_TOKEN_CONFIGURED': bool(config.get('SANKHYA_TOKEN')),
            'WEBHOOK_SECRET_CONFIGURED': bool(config.get('WEBHOOK_SECRET')),
            'TRANSPORTADORAS_ENABLED': True
        }
        
        return jsonify({
            "status": "success",
            "config": safe_config,
            "version": "2.2",
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# SUBSTITUA a rota /woo/orders no app.py por esta versão corrigida:

@app.route("/woo/orders", methods=["GET"])
def woo_orders():
    """Lista pedidos do WooCommerce (requer token) - VERSÃO CORRIGIDA"""
    token = token_da_requisicao()
    if not token_valido(token):
        return jsonify({"erro": "Token inválido"}), 401
    
    try:
        # CORREÇÃO: Usa o WooCommerceService que já tem as correções de URL
        woo_service = WooCommerceService()
        
        # Parmetros opcionais
        params = {
            'per_page': int(request.args.get('per_page', 10)),
            'orderby': 'date',
            'order': 'desc'
        }
        
        # Adiciona filtro de status se fornecido
        status = request.args.get('status')
        if status and status != 'any':
            params['status'] = status
        
        logger.info(f"Buscando pedidos WooCommerce com filtros: {params}")
        
        # USA O SERVIÇO CORRIGIDO em vez da função get_orders()
        resultado = woo_service.buscar_pedidos(
            status=status, 
            limit=params['per_page']
        )
        
        if resultado['status'] == 'success':
            return jsonify({
                "status": "success",
                "orders": resultado['pedidos'],
                "total": resultado['total'],
                "timestamp": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": resultado.get('message', 'Erro ao buscar pedidos'),
                "timestamp": datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        logger.error(f"Erro na rota /woo/orders: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# REMOVA ou comente a função get_orders() antiga se não for usada em outros lugares

@app.route("/sankhya/transportadoras", methods=["GET"])
def sankhya_transportadoras():
    """Lista transportadoras ativas no Sankhya (requer token)"""
    token = token_da_requisicao()
    if not token_valido(token):
        return jsonify({"erro": "Token inválido"}), 401
    
    try:
        logger.info("Listando transportadoras do Sankhya")
        
        with SankhyaService.with_auth() as sankhya:
            # Lista transportadoras ativas
            transportadoras = sankhya.transportadoras.listar_transportadoras_ativas(20)
            
            # Converte para formato mais legível
            transportadoras_formatadas = []
            for transp in transportadoras:
                transp_info = {
                    'codparc': transp['f0']['$'],
                    'nome': transp['f1']['$'],
                    'id_allpost': transp['f2'].get('$', 'N/A')
                }
                transportadoras_formatadas.append(transp_info)
            
            logger.info(f"Encontradas {len(transportadoras_formatadas)} transportadoras")
            
            return jsonify({
                "status": "success",
                "count": len(transportadoras_formatadas),
                "transportadoras": transportadoras_formatadas,
                "timestamp": datetime.now().isoformat()
            }), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar transportadoras: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/sankhya/stats", methods=["GET"])
def sankhya_stats():
    """Estatísticas do sistema Sankhya (requer token)"""
    token = token_da_requisicao()
    if not token_valido(token):
        return jsonify({"erro": "Token inválido"}), 401
    
    try:
        logger.info("Obtendo estatísticas do Sankhya")
        
        with SankhyaService.with_auth() as sankhya:
            stats = sankhya.obter_estatisticas_sistema()
            
            return jsonify({
                "status": "success",
                "statistics": stats,
                "timestamp": datetime.now().isoformat()
            }), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/sankhya/test", methods=["POST"])
def sankhya_test():
    """Teste de integração Sankhya (requer token)"""
    token = token_da_requisicao()
    if not token_valido(token):
        return jsonify({"erro": "Token inválido"}), 401
    
    try:
        logger.info("Testando integração Sankhya")
        
        with SankhyaService.with_auth() as sankhya:
            # Verifica configuração geral
            config_ok = sankhya.verificar_configuracao()
            
            # Testa busca de transportadora específica se fornecida
            test_results = {
                "configuracao_geral": config_ok,
                "testes_realizados": []
            }
            
            # Teste 1: Cidade padrão
            try:
                cidade = sankhya.cidades.obter_cidade_padrao_robusta()
                test_results["testes_realizados"].append({
                    "teste": "cidade_padrao",
                    "sucesso": bool(cidade),
                    "resultado": f"{cidade['NOMECID']}/{cidade['UF']}" if cidade else "Não encontrada"
                })
            except Exception as e:
                test_results["testes_realizados"].append({
                    "teste": "cidade_padrao",
                    "sucesso": False,
                    "erro": str(e)
                })
            
            # Teste 2: Transportadoras
            try:
                transportadoras = sankhya.transportadoras.listar_transportadoras_ativas(3)
                test_results["testes_realizados"].append({
                    "teste": "transportadoras",
                    "sucesso": len(transportadoras) > 0,
                    "resultado": f"{len(transportadoras)} transportadoras encontradas"
                })
            except Exception as e:
                test_results["testes_realizados"].append({
                    "teste": "transportadoras",
                    "sucesso": False,
                    "erro": str(e)
                })
            
            # Teste 3: Busca por ID AllPost específico (se fornecido)
            id_allpost = request.json.get('id_allpost') if request.json else None
            if id_allpost:
                try:
                    transportadora = sankhya.transportadoras.consultar_por_id_allpost(id_allpost)
                    test_results["testes_realizados"].append({
                        "teste": f"transportadora_id_{id_allpost}",
                        "sucesso": bool(transportadora),
                        "resultado": f"{transportadora['NOMEPARC']} ({transportadora['CODPARC']})" if transportadora else "Não encontrada"
                    })
                except Exception as e:
                    test_results["testes_realizados"].append({
                        "teste": f"transportadora_id_{id_allpost}",
                        "sucesso": False,
                        "erro": str(e)
                    })
            
            logger.info(f"Teste concluído - Config OK: {config_ok}")
            
            return jsonify({
                "status": "success",
                "test_results": test_results,
                "timestamp": datetime.now().isoformat()
            }), 200
        
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
        
@app.route("/woo/customers", methods=["GET"])
def woo_customers():
    """Lista clientes do WooCommerce (requer token)"""
    token = token_da_requisicao()
    if not token_valido(token):
        return jsonify({"erro": "Token inválido"}), 401
    
    try:
        # Parmetros opcionais da URL
        params = {
            'per_page': int(request.args.get('per_page', 10)),
            'page': int(request.args.get('page', 1)),
            'orderby': request.args.get('orderby', 'registered_date'),
            'order': request.args.get('order', 'desc'),
            'search': request.args.get('search'),
            'email': request.args.get('email'),
            'role': request.args.get('role', 'customer')
        }
        
        # Remove parmetros vazios
        params = {k: v for k, v in params.items() if v is not None}
        
        logger.info(f"Buscando clientes WooCommerce com filtros: {params}")
        
        # Usar o serviço WooCommerce
        woo_service = WooCommerceService()
        resultado = woo_service.buscar_clientes(limit=params.get('per_page', 10))
        
        if resultado['status'] == 'success':
            clientes = resultado['clientes']
            
            # Formatar resposta com informações úteis
            clientes_formatados = []
            for cliente in clientes:
                cliente_info = {
                    'id': cliente.get('id'),
                    'nome_completo': f"{cliente.get('first_name', '')} {cliente.get('last_name', '')}".strip(),
                    'email': cliente.get('email'),
                    'telefone': cliente.get('billing', {}).get('phone'),
                    'data_cadastro': cliente.get('date_created'),
                    'total_pedidos': cliente.get('orders_count', 0),
                    'total_gasto': cliente.get('total_spent', '0.00'),
                    'endereco': {
                        'cidade': cliente.get('billing', {}).get('city'),
                        'estado': cliente.get('billing', {}).get('state'),
                        'cep': cliente.get('billing', {}).get('postcode'),
                        'endereco': cliente.get('billing', {}).get('address_1')
                    },
                    'documento': cliente.get('meta_data', [])  # CPF/CNPJ pode estar aqui
                }
                clientes_formatados.append(cliente_info)
            
            return jsonify({
                "status": "success",
                "clientes": clientes_formatados,
                "total": len(clientes_formatados),
                "filtros_aplicados": params,
                "timestamp": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": resultado.get('message', 'Erro ao buscar clientes'),
                "timestamp": datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        logger.error(f"Erro ao buscar clientes: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/woo/customers/<int:customer_id>", methods=["GET"])
def woo_customer_detail(customer_id):
    """Busca cliente específico por ID (requer token)"""
    token = token_da_requisicao()
    if not token_valido(token):
        return jsonify({"erro": "Token inválido"}), 401
    
    try:
        logger.info(f"Buscando cliente específico: {customer_id}")
        
        woo_service = WooCommerceService()
        client = woo_service.client
        
        # Buscar cliente específico
        cliente = client.get_customer(customer_id)
        
        if cliente:
            # Buscar pedidos do cliente
            pedidos = client.get_orders({'customer': customer_id, 'per_page': 100})
            
            # Formatar resposta detalhada
            cliente_detalhado = {
                'informacoes_basicas': {
                    'id': cliente.get('id'),
                    'nome_completo': f"{cliente.get('first_name', '')} {cliente.get('last_name', '')}".strip(),
                    'email': cliente.get('email'),
                    'username': cliente.get('username'),
                    'data_cadastro': cliente.get('date_created'),
                    'data_modificacao': cliente.get('date_modified'),
                    'avatar_url': cliente.get('avatar_url')
                },
                'estatisticas': {
                    'total_pedidos': cliente.get('orders_count', 0),
                    'total_gasto': cliente.get('total_spent', '0.00'),
                    'pedidos_encontrados': len(pedidos) if pedidos else 0
                },
                'endereco_cobranca': cliente.get('billing', {}),
                'endereco_entrega': cliente.get('shipping', {}),
                'meta_dados': cliente.get('meta_data', []),
                'pedidos_recentes': [
                    {
                        'id': p.get('id'),
                        'status': p.get('status'),
                        'total': p.get('total'),
                        'data': p.get('date_created')
                    } for p in (pedidos[:5] if pedidos else [])
                ]
            }
            
            return jsonify({
                "status": "success",
                "cliente": cliente_detalhado,
                "timestamp": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": f"Cliente {customer_id} não encontrado",
                "timestamp": datetime.now().isoformat()
            }), 404
        
    except Exception as e:
        logger.error(f"Erro ao buscar cliente {customer_id}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/sync/orders", methods=["POST"])
def sync_orders():
    """Sincronização manual de pedidos (requer token)"""
    token = token_da_requisicao()
    if not token_valido(token):
        return jsonify({"erro": "Token inválido"}), 401
    
    try:
        logger.info("Iniciando sincronização manual de pedidos")
        
        # Usa o serviço WooCommerce para sincronizar
        woo_service = WooCommerceService()
        resultados = woo_service.sincronizar_pedidos_pendentes()
        
        # Conta sucessos e erros
        sucessos = sum(1 for r in resultados if r.get('resultado', {}).get('status') == 'success')
        erros = len(resultados) - sucessos
        
        # Conta quantos tinham transportadora
        com_transportadora = sum(1 for r in resultados 
                               if r.get('resultado', {}).get('transportadora_info'))
        
        logger.info(f"Sincronização concluída: {sucessos} sucessos, {erros} erros, {com_transportadora} com transportadora")
        
        return jsonify({
            "status": "success",
            "message": "Sincronização concluída",
            "total_processados": len(resultados),
            "sucessos": sucessos,
            "erros": erros,
            "com_transportadora": com_transportadora,
            "detalhes": resultados,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na sincronização: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handler para rotas não encontradas"""
    return jsonify({
        "status": "error",
        "message": "Endpoint não encontrado",
        "path": request.path,
        "method": request.method,
        "suggestion": "Verifique GET / para lista de endpoints disponíveis"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handler para métodos não permitidos"""
    return jsonify({
        "status": "error",
        "message": "Método não permitido para este endpoint",
        "path": request.path,
        "method": request.method,
        "allowed_methods": error.description if hasattr(error, 'description') else 'unknown'
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    logger.error(f"Erro interno: {error}")
    return jsonify({
        "status": "error",
        "message": "Erro interno do servidor",
        "timestamp": datetime.now().isoformat()
    }), 500

if __name__ == "__main__":
    logger.info("Iniciando WooCommerce-Sankhya Integration v2.2")
    logger.info(f"Ambiente: {config.get('USAR_AMBIENTE', 'não configurado')}")
    logger.info(f"WooCommerce: {config.get('WC_URL', 'não configurado')}")
    logger.info(f"Sankhya: {config.get('SANKHYA_BASE_URL', 'não configurado')}")
    logger.info(f"Webhooks registrados em: /webhook/")
    logger.info(f"Novo: Suporte a transportadoras AllPost")
    logger.info(f"Novo: TIPMOV = P (Pedido)")
    
    # Configurações do servidor
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 3000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    logger.info(f"Servidor rodando em {host}:{port}")
    
    app.run(host=host, port=port, debug=debug)
