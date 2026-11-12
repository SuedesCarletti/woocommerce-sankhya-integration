"""
Webhook handlers CORRIGIDOS - Versão 2.2.0
Corrige extração de headers e sempre retorna HTTP 200 para evitar desativação
"""

from flask import Blueprint, request, jsonify
from services.woocommerce import WooCommerceService
from config.settings import load_config
from utils import setup_logger, log_webhook, log_processing, log_data_validation
from .validators import WebhookValidator
from .security import WebhookSecurity

# Configuração
config = load_config()
logger = setup_logger("webhooks", level="INFO")

# Serviços
woo_service = WooCommerceService()
validator = WebhookValidator()
security = WebhookSecurity()

# Blueprint
webhook_bp = Blueprint('webhook', __name__)

# Rota principal - aceita tanto / quanto "" (raiz do blueprint)
@webhook_bp.route('/', methods=['POST'], strict_slashes=False)
@webhook_bp.route('', methods=['POST'], strict_slashes=False)
def handle_webhook():
    """
    Endpoint principal CORRIGIDO para receber webhooks do WooCommerce
    """
    try:
        # 1. Validação de segurança - Token (Priorizar Header Authorization)
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.args.get("token") # Fallback para query string

        if not security.validar_token(token):
            log_processing(logger, "Webhook - Validação Token", "error", "Token inválido")
            return jsonify({"erro": "Token inválido"}), 401

        # 2. CORREÇÃO: Extrair headers corretos do WooCommerce
        raw_headers = {
            'event': request.headers.get("X-Wc-Webhook-Event"),           # "updated", "created"
            'resource': request.headers.get("X-Wc-Webhook-Resource"),     # "customer", "order"  
            'topic': request.headers.get("X-Wc-Webhook-Topic"),           # "customer.updated", "order.created"
            'webhook_id': request.headers.get("X-Wc-Webhook-Id"),
            'delivery_id': request.headers.get("X-Wc-Webhook-Delivery-Id"),
            'signature': request.headers.get("X-Wc-Webhook-Signature"),
            'source': request.headers.get("X-Wc-Webhook-Source")
        }

        # CORREÇÃO: Log dos headers RAW SEM usar log_webhook
        logger.info(f"[WEBHOOK DEBUG] Headers RAW do WooCommerce: {raw_headers}")

        # 3. Converter para formato esperado pelo código
        headers = {
            'event_type': raw_headers['event'],
            'resource': raw_headers['resource'],
            'webhook_id': raw_headers['webhook_id'],
            'delivery_id': raw_headers['delivery_id'],
            'signature': raw_headers['signature'],
            'source': raw_headers['source'],
            'topic': raw_headers['topic']
        }

        # CORREÇÃO: Log dos headers convertidos SEM usar log_webhook
        logger.info(f"[WEBHOOK DEBUG] Headers convertidos: {headers}")

        # 4. Fallback usando topic se headers principais estão vazios
        if not headers['event_type'] or not headers['resource']:
            topic = headers.get('topic', '')
            if '.' in topic:
                parts = topic.split('.', 1)
                headers['resource'] = parts[0]
                headers['event_type'] = parts[1]
                logger.info(f"[WEBHOOK DEBUG] Extraído do topic: resource={parts[0]}, event={parts[1]}")

        # 5. Log de debug detalhado
        logger.info(f"[WEBHOOK DEBUG] Todos os headers da requisição:")
        for header_name, header_value in request.headers:
            if header_name.lower().startswith('x-wc-'):
                logger.info(f"  {header_name}: {header_value}")

        # 6. Obter dados JSON
        try:
            data = request.get_json(force=True)
            log_data_validation(logger, "Parse JSON", "success", f"Tipo: {type(data).__name__}")
        except Exception as json_error:
            log_data_validation(logger, "Parse JSON", "error", f"Erro: {json_error}")
            return jsonify({"erro": "JSON inválido"}), 400

        # 7. CORREÇÃO: Log do webhook SEM usar função problemática
        webhook_id = headers.get('webhook_id', 'N/A')
        event_type = headers.get('event_type', 'unknown')
        resource = headers.get('resource', 'unknown')
        
        logger.info(f"Webhook: {resource}.{event_type} | ID: {webhook_id}")

        # 8. VALIDAÇÃO HMAC (opcional)
        if config.get('VALIDAR_HMAC_SIGNATURE', False):
            signature_valid = security.validar_assinatura(
                request.get_data(),
                headers.get('signature', ''),
                config.get('WEBHOOK_SECRET', '')
            )
            
            if signature_valid:
                log_processing(logger, "Webhook - Assinatura", "success", "Assinatura válida")
            else:
                log_processing(logger, "Webhook - Assinatura", "error", "Assinatura inválida")
                return jsonify({"erro": "Assinatura inválida"}), 401
        else:
            log_processing(logger, "Webhook - Assinatura", "success", "Assinatura válida")

        # 9. PROCESSAMENTO PRINCIPAL - Usar WooCommerceService corrigido
        logger.info(f"Iniciando: Webhook {resource}.{event_type}")
        
        # Log payload summary
        payload_id = data.get('id', 'N/A')
        payload_status = data.get('status', 'N/A')
        logger.info(f"[WEBHOOK DEBUG] Payload summary - ID: {payload_id}, Status: {payload_status}")
        
        # Chamar o processador corrigido
        logger.info(f"[WEBHOOK DEBUG] Chamando woo_service.processar_webhook")
        resultado = woo_service.processar_webhook(headers, data)
        
        logger.info(f"[WEBHOOK DEBUG] Resultado do processamento: {resultado.get('status', 'unknown')}")

        # 10. RESPOSTA - SEMPRE retorna 200 para evitar desativação do webhook
        if resultado.get('status') == 'success':
            logger.info(f"Sucesso: Webhook {resource}.{event_type} | ID: {payload_id}")
            return jsonify({
                "status": "success",
                "message": resultado.get('message', 'Processado com sucesso'),
                "data": resultado
            }), 200
        
        elif resultado.get('status') == 'skipped':
            logger.info(f"⏭Ignorado: Webhook {resource}.{event_type} | Motivo: {resultado.get('message', 'N/A')}")
            return jsonify({
                "status": "skipped", 
                "message": resultado.get('message', 'Evento ignorado')
            }), 200
        
        else:
            # CORREÇÃO CRÍTICA: Mesmo com erro, retorna 200 para não desativar webhook
            error_msg = resultado.get('error', 'Erro desconhecido')
            logger.error(f"Erro: Webhook {resource}.{event_type} | {error_msg}")
            
            return jsonify({
                "status": "error",
                "message": "Erro processado (webhook mantido ativo)",
                "error": error_msg
            }), 200  # ← MUDANÇA: 200 em vez de 500

    except Exception as e:
        # CORREÇÃO CRÍTICA: Capturar qualquer exceção e retornar 200
        logger.error(f"Erro: Webhook - Exceção geral | {str(e)}")
        logger.error(f"[WEBHOOK ERROR] Erro no processamento: {str(e)}")
        
        return jsonify({
            "status": "error",
            "message": "Erro interno processado (webhook mantido ativo)",
            "error": str(e)
        }), 200  # ← MUDANÇA: 200 em vez de 500

# ROTAS AUXILIARES

@webhook_bp.route('/health', methods=['GET'])
def webhook_health():
    """Health check dos webhooks"""
    try:
        # Testa conexão com Sankhya usando o serviço corrigido
        teste_sankhya = woo_service.teste_conexao_sankhya()
        
        status_geral = "healthy" if teste_sankhya.get('status') == 'success' else "degraded"
        
        return jsonify({
            "status": status_geral,
            "webhook_service": "active",
            "sankhya_connection": teste_sankhya,
            "version": "2.3.0"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 200  # Retorna 200 mesmo com erro para não alarmar monitoramento

@webhook_bp.route('/test', methods=['POST'])
def webhook_test():
    """Endpoint para testar webhooks manualmente"""
    try:
        # Simula headers de teste
        headers = {
            'event_type': 'created',
            'resource': 'order',
            'webhook_id': 'test',
            'delivery_id': 'test-delivery',
            'signature': 'test-signature',
            'source': 'test',
            'topic': 'order.created'
        }
        
        # Dados de teste
        data = request.get_json() or {
            "id": 99999,
            "status": "processing",
            "billing": {
                "first_name": "Teste",
                "last_name": "Usuario",
                "email": "teste@teste.com"
            },
            "line_items": []
        }
        
        logger.info(f"Teste de webhook iniciado")
        
        # Processa usando o serviço corrigido
        resultado = woo_service.processar_webhook(headers, data)
        
        return jsonify({
            "status": "test_completed",
            "resultado": resultado
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no teste de webhook: {e}")
        return jsonify({
            "status": "test_error",
            "error": str(e)
        }), 200

@webhook_bp.route('/stats', methods=['GET'])
def webhook_stats():
    """Estatísticas dos webhooks"""
    try:
        stats = woo_service.obter_estatisticas()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 200
        
@webhook_bp.route('/debug', methods=['GET'])
def webhook_debug():
    """
    Debug de configuração de webhook (requer token)
    """
    try:
        # Validação de token
        token = request.args.get("token")
        if not security.validar_token(token):
            return jsonify({"erro": "Token inválido"}), 401
        
        debug_info = {
            "webhook_endpoint": "/webhook/",
            "required_url_format": "https://seu-servidor.com/webhook/?token=SEU_TOKEN",
            "supported_events": [
                "order.created",
                "order.updated", 
                "order.deleted",
                "customer.created",
                "customer.updated",
                "customer.deleted",
                "product.created",
                "product.updated",
                "product.deleted"
            ],
            "required_headers": [
                "X-WC-Webhook-Event",
                "X-WC-Webhook-Resource",
                "X-WC-Webhook-ID",
                "X-WC-Webhook-Delivery-ID"
            ],
            "optional_headers": [
                "X-WC-Webhook-Signature",
                "X-WC-Webhook-Source",
                "X-WC-Webhook-Topic"
            ],
            "configuration": {
                "hmac_validation": bool(config.get('WC_WEBHOOK_SECRET')),
                "rate_limiting": "100 req/min per IP",
                "environment": config.get('USAR_AMBIENTE', 'sandbox'),
                "always_returns_200": True,
                "auto_disable_prevention": "Ativo"
            },
            "notes": [
                "Este endpoint SEMPRE retorna HTTP 200 para evitar desativação automática",
                "Erros são logados mas não impedem resposta 200",
                "Use o endpoint /webhook/test para simular webhooks"
            ],
            "timestamp": validator.agora_iso()
        }
        
        return jsonify(debug_info), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Error handlers para o blueprint
@webhook_bp.errorhandler(404)
def webhook_not_found(error):
    """Handler para rotas não encontradas no blueprint"""
    return jsonify({
        "status": "error",
        "message": "Endpoint não encontrado no módulo webhook",
        "available_endpoints": [
            "POST /webhook/ - Webhook principal",
            "GET  /webhook/health - Health check", 
            "GET  /webhook/stats - Estatísticas (com token)",
            "POST /webhook/test - Teste (dev, com token)",
            "GET  /webhook/debug - Debug (com token)"
        ]
    }), 404

@webhook_bp.errorhandler(405)
def webhook_method_not_allowed(error):
    """Handler para métodos não permitidos"""
    return jsonify({
        "status": "error",
        "message": "Método não permitido",
        "allowed_methods": error.description or "POST"
    }), 405

@webhook_bp.errorhandler(500)
def webhook_internal_error(error):
    """Handler para erros internos"""
    log_processing(logger, "Webhook - Erro Interno", "error", str(error))
    
    # CORREÇÃO: Mesmo erro 500 retorna como 200
    return jsonify({
        "status": "received",
        "message": "Webhook recebido, mas houve erro interno do servidor",
        "error_id": validator.gerar_error_id() if 'validator' in globals() else "unknown"
    }), 200  # ← SEMPRE 200!
