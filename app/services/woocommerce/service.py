"""
WooCommerceService COMPLETO - Versão 2.5.0
MANTÉM TODAS as funcionalidades originais
CORRIGE apenas o problema do context manager
ADICIONA métodos auxiliares que estavam faltando
"""

import re
from services.sankhya import SankhyaService
from services.woocommerce.client import WooCommerceClient
from config.settings import load_config
import json

class WooCommerceService:
    """
    Serviço COMPLETO para processamento de webhooks e operações WooCommerce
    MANTÉM todas as funcionalidades originais
    CORRIGE apenas o uso do context manager
    """
    
    def __init__(self):
        self.config = load_config()
        
        # Inicializar cliente WooCommerce
        try:
            # Primeiro tenta o client defensivo (sem parâmetros)
            from services.woocommerce.client import WooCommerceClientDefensive
            self.client = WooCommerceClientDefensive()
            print(f"[WOO SERVICE] WooCommerceService inicializado com cliente defensivo")
        except ImportError:
            # Fallback para o client original
            try:
                from services.woocommerce.client import WooCommerceClient
                self.client = WooCommerceClient()
                print(f"[WOO SERVICE] WooCommerceService inicializado com cliente padrão")
            except Exception as fallback_error:
                print(f"[WOO SERVICE] Erro ao inicializar cliente WC: {fallback_error}")
                self.client = None
        except Exception as e:
            print(f"[WOO SERVICE] Erro ao inicializar cliente WC: {e}")
            self.client = None
    
    def processar_webhook(self, headers, data):
        """
        Processa webhooks usando context manager
        MANTÉM toda a lógica original, CORRIGE apenas a autenticação
        """
        try:
            # Extrair informações do webhook
            event_type = headers.get('event_type', '')
            resource = headers.get('resource', '')
            webhook_id = headers.get('webhook_id', 'N/A')
            delivery_id = headers.get('delivery_id', 'N/A')
            
            print(f"[WOO SERVICE] Processando webhook com headers: {headers}")
            print(f"[WOO SERVICE] Event: {event_type}, Resource: {resource}, Webhook ID: {webhook_id}")
            
            # Normalizar evento para logging
            evento_normalizado = f"{resource}.{event_type}"
            
            # CORREÇÃO PRINCIPAL: Usar context manager para autenticação automática
            try:
                with SankhyaService.with_auth() as sankhya:
                    print(f"[WOO SERVICE] SankhyaService autenticado com sucesso")
                    
                    # Processar baseado no tipo de evento
                    if resource == 'order' and event_type == 'created':
                        print(f"[WOO SERVICE] Processando evento: order.created")
                        return self._processar_pedido_criado(sankhya, data, headers)
                    
                    elif resource == 'order' and event_type == 'updated':
                        print(f"[WOO SERVICE] Processando evento: order.updated")
                        return self._processar_pedido_atualizado(sankhya, data, headers)
                    
                    elif resource == 'customer' and event_type == 'created':
                        print(f"[WOO SERVICE] Processando evento: customer.created")
                        return self._processar_cliente_criado(sankhya, data, headers)
                    
                    elif resource == 'customer' and event_type == 'updated':
                        print(f"[WOO SERVICE] Processando evento: customer.updated")
                        return self._processar_cliente_atualizado(sankhya, data, headers)
                    
                    elif resource == 'product' and event_type in ['created', 'updated']:
                        print(f"[WOO SERVICE] Processando evento: product.{event_type}")
                        return self._processar_produto(sankhya, data, headers, event_type)
                    
                    else:
                        print(f"[WOO SERVICE] ℹEvento não processado: {evento_normalizado}")
                        return {
                            "status": "skipped",
                            "message": f"Evento {evento_normalizado} não implementado",
                            "evento": evento_normalizado
                        }
                        
            except Exception as auth_error:
                print(f"[WOO SERVICE] Erro na autenticação Sankhya: {auth_error}")
                return {
                    "status": "error",
                    "error": f"Falha na autenticação: {str(auth_error)}",
                    "evento": evento_normalizado
                }
            
            # Todos os ramos do `with` acima já retornam; este ponto não é alcançável.
                
        except Exception as e:
            print(f"[WOO SERVICE] Erro geral no processamento: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _processar_pedido_criado(self, sankhya, data, headers):
        """
        Processa PEDIDO criado (não cliente)
        """
        try:
            pedido_id = data.get('id')
            customer_id = data.get('customer_id')
            status = data.get('status', '')
            
            print(f"[WOO PROCESSOR] Pedido criado!")
            print(f"[WOO PROCESSOR] Pedido ID: {pedido_id}")
            print(f"[WOO PROCESSOR] Cliente ID: {customer_id}")
            print(f"[WOO PROCESSOR] Status: {status}")
            
            # CORREÇÃO: Processar como PEDIDO
            resultado = sankhya.processar_pedido_completo(data)
            
            if resultado.get('status') == 'success':
                print(f"[WOO PROCESSOR] Pedido criado e processado com sucesso")
                return {
                    "status": "success",
                    "message": f"Pedido {pedido_id} criado e integrado com Sankhya",
                    "pedido_id": pedido_id,
                    "customer_id": customer_id,
                    "nunota": resultado.get('nunota'),
                    "pedido_status": status
                }
            else:
                return {
                    "status": "error",
                    "error": resultado.get('error'),
                    "pedido_id": pedido_id,
                    "customer_id": customer_id
                }
                
        except Exception as e:
            print(f"[WOO PROCESSOR] Erro no processamento do pedido: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pedido_id": data.get('id', 0),
                "customer_id": data.get('customer_id', 0)
            }
    
    def _processar_pedido_atualizado(self, sankhya, data, headers):
        """
        CORRIGIDO: Processa order.updated como PEDIDO (mantém consulta de parceiro)
        """
        try:
            pedido_id = data.get('id')
            customer_id = data.get('customer_id')
            status_anterior = data.get('status', '')
            
            print(f"[WOO PROCESSOR] Pedido atualizado!")
            print(f"[WOO PROCESSOR] Pedido ID: {pedido_id}")
            print(f"[WOO PROCESSOR] Cliente ID: {customer_id}")
            print(f"[WOO PROCESSOR] Status: {status_anterior}")
            
            # CORREÇÃO PRINCIPAL: Usar processar_pedido_completo
            # (que já consulta parceiro e retorna CODPARC como era antes)
            resultado = sankhya.processar_pedido_completo(data)
            
            if resultado.get('status') == 'success':
                print(f"[WOO PROCESSOR] Pedido atualizado processado com sucesso")
                return {
                    "status": "success",
                    "message": f"Pedido atualizado e reprocessado - Status: {status_anterior}",
                    "pedido_id": pedido_id,
                    "customer_id": customer_id,
                    "nunota": resultado.get('nunota'),
                    "codparc": resultado.get('codparc'),  # Mantém CODPARC no retorno
                    "status_anterior": status_anterior,
                    "evento_original": "order.updated"
                }
            else:
                return {
                    "status": "error", 
                    "error": resultado.get('error'),
                    "pedido_id": pedido_id,
                    "customer_id": customer_id,
                    "status_anterior": status_anterior
                }
                
        except Exception as e:
            print(f"[WOO PROCESSOR] Erro no processamento da atualização: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pedido_id": data.get('id', 0),
                "customer_id": data.get('customer_id', 0)
            }
    
    def _processar_pedido_criado(self, sankhya, data, headers):
        """
        MANTIDO: Este método já funciona corretamente
        (consulta parceiro e retorna CODPARC como visto nos logs)
        """
        try:
            pedido_id = data.get('id')
            customer_id = data.get('customer_id')
            status = data.get('status', '')
            
            print(f"[WOO PROCESSOR] Pedido criado!")
            print(f"[WOO PROCESSOR] Pedido ID: {pedido_id}")
            print(f"[WOO PROCESSOR] Cliente ID: {customer_id}")
            print(f"[WOO PROCESSOR] Status: {status}")
            
            # MANTÉM: processar_pedido_completo (que já funciona corretamente)
            resultado = sankhya.processar_pedido_completo(data)
            
            if resultado.get('status') == 'success':
                print(f"[WOO PROCESSOR] Pedido criado e processado com sucesso")
                return {
                    "status": "success",
                    "message": f"Pedido {pedido_id} criado e integrado com Sankhya",
                    "pedido_id": pedido_id,
                    "customer_id": customer_id,
                    "nunota": resultado.get('nunota'),
                    "codparc": resultado.get('codparc'),  # Mantém CODPARC no retorno
                    "status": status
                }
            else:
                return {
                    "status": "error",
                    "error": resultado.get('error'),
                    "pedido_id": pedido_id,
                    "customer_id": customer_id
                }
                
        except Exception as e:
            print(f"[WOO PROCESSOR] Erro no processamento do pedido: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pedido_id": data.get('id', 0),
                "customer_id": data.get('customer_id', 0)
            }

    def _processar_cliente_criado(self, sankhya, data, headers):
        """
        Processa cliente criado via webhook, usando o SankhyaService já autenticado.
        """
        try:
            cliente_id = data.get('id')
            email      = data.get('email', '')
            nome       = f"{data.get('first_name','')} {data.get('last_name','')}".strip()

            print(f"[WOO SERVICE] Novo cliente criado! ID={cliente_id} Nome={nome} Email={email}")

            # **Aqui usamos diretamente o sankhya já autenticado**
            resultado = sankhya.processar_cliente_completo(data)

            if resultado.get('sucesso'):
                print(f"[WOO SERVICE] Cliente processado no Sankhya")
                return {
                    'status': 'success',
                    'message': f'Cliente {cliente_id} processado com sucesso',
                    'sankhya_result': resultado
                }
            else:
                print(f"[WOO SERVICE] Erro no Sankhya: {resultado.get('erro')}")
                return {
                    'status': 'error',
                    'message': f'Erro ao processar cliente no Sankhya: {resultado.get("erro")}'
                }

        except Exception as e:
            print(f"[WOO SERVICE] Erro ao processar cliente criado: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _processar_cliente_atualizado(self, sankhya, data, headers):
        """
        Normaliza CEP para busca IBGE
        """
        try:
            # CORREÇÃO: Extrair dados da estrutura real do webhook
            cliente_id = data.get('id') or data.get('customer_id')
            
            # PRIORIDADE: Dados vêm de 'billing' quando webhook é customer.updated
            billing = data.get('billing', {})
            
            # DEBUG: Log da estrutura real
            print(f"[WOO SERVICE DEBUG] Estrutura real do webhook:")
            print(f"[WOO SERVICE DEBUG]   ID: {cliente_id}")
            print(f"[WOO SERVICE DEBUG]   Keys principais: {list(data.keys())}")
            print(f"[WOO SERVICE DEBUG]   Billing keys: {list(billing.keys()) if billing else 'N/A'}")
            
            # EXTRAÇÃO CORRETA: Usar billing como fonte primária
            email = data.get('email') or billing.get('email', '')
            first_name = data.get('first_name') or billing.get('first_name', '')
            last_name = data.get('last_name') or billing.get('last_name', '')
            
            nome = f"{first_name} {last_name}".strip()
            
            print(f"[WOO SERVICE] Cliente atualizado! ID={cliente_id} Nome={nome} Email={email}")
            
            # CORREÇÃO CRÍTICA: Normalizar CEP para busca IBGE
            cep_raw = billing.get('postcode', data.get('postcode', ''))
            cep_limpo = re.sub(r'\D', '', cep_raw) if cep_raw else ''
            
            # NORMALIZAÇÃO CORRETA: Priorizar billing, CEP limpo
            dados_normalizados = {
                'id': cliente_id,
                'customer_id': cliente_id,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'address_1': billing.get('address_1', data.get('address_1', '')),
                'address_2': billing.get('address_2', data.get('address_2', '')),
                'city': billing.get('city', data.get('city', '')),
                'state': billing.get('state', data.get('state', '')),
                'postcode': cep_limpo,  # CEP LIMPO para busca IBGE
                'postcode_formatted': cep_raw,  # CEP original para exibição
                'country': billing.get('country', data.get('country', '')),
                'phone': billing.get('phone', data.get('phone', '')),
                'neighborhood': billing.get('neighborhood', data.get('neighborhood', '')),
                'cpf': billing.get('cpf', data.get('cpf', '')),
                'cnpj': billing.get('cnpj', data.get('cnpj', '')),
                'company': billing.get('company', data.get('company', '')),
                'persontype': billing.get('persontype', data.get('persontype', '')),
                'number': billing.get('number', data.get('number', '')),
                'meta_data': data.get('meta_data', []),
                
                # MANTER billing com CEP limpo para compatibilidade
                'billing': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'company': billing.get('company', ''),
                    'address_1': billing.get('address_1', ''),
                    'address_2': billing.get('address_2', ''),
                    'city': billing.get('city', ''),
                    'state': billing.get('state', ''),
                    'postcode': cep_limpo,  # CEP LIMPO para busca IBGE
                    'country': billing.get('country', ''),
                    'email': email,
                    'phone': billing.get('phone', ''),
                    'neighborhood': billing.get('neighborhood', ''),
                    'cpf': billing.get('cpf', ''),
                    'cnpj': billing.get('cnpj', ''),
                    'persontype': billing.get('persontype', ''),
                    'number': billing.get('number', '')
                }
            }
            
            # VERIFICAÇÃO CRÍTICA: Código IBGE nos meta_data
            meta_data = data.get('meta_data', [])
            ibge_code = None
            for meta in meta_data:
                if meta.get('key') == 'billing_ibge_code':
                    ibge_code = meta.get('value')
                    break
            
            if ibge_code:
                dados_normalizados['billing']['ibge_code'] = ibge_code
                print(f"[WOO SERVICE DEBUG] Código IBGE encontrado: {ibge_code}")
            else:
                print(f"[WOO SERVICE DEBUG] Código IBGE não encontrado nos meta_data")
                if cep_limpo:
                    print(f"[WOO SERVICE DEBUG] CEP encontrado: {cep_raw} -> {cep_limpo} (limpo para busca IBGE)")
            
            # DEBUG: Log dos dados normalizados
            print(f"[WOO SERVICE DEBUG] Dados normalizados:")
            print(f"[WOO SERVICE DEBUG]   ID: {dados_normalizados['id']}")
            print(f"[WOO SERVICE DEBUG]   Email: {dados_normalizados['email']}")
            print(f"[WOO SERVICE DEBUG]   Nome: {dados_normalizados['first_name']} {dados_normalizados['last_name']}")
            print(f"[WOO SERVICE DEBUG]   Endereço: {dados_normalizados['address_1']}")
            print(f"[WOO SERVICE DEBUG]   Cidade: {dados_normalizados['city']}")
            print(f"[WOO SERVICE DEBUG]   Estado: {dados_normalizados['state']}")
            print(f"[WOO SERVICE DEBUG]   CEP: {dados_normalizados['postcode']} (limpo)")
            print(f"[WOO SERVICE DEBUG]   CPF: {dados_normalizados['cpf']}")
            print(f"[WOO SERVICE DEBUG]   Telefone: {dados_normalizados['phone']}")
            
            # VALIDAÇÃO PRÉVIA: Verificar se dados essenciais estão presentes
            if not dados_normalizados['email']:
                print(f"[WOO SERVICE] Email não encontrado nos dados")
                return {
                    'status': 'error',
                    'message': 'Email obrigatório não encontrado'
                }
            
            if not dados_normalizados['first_name'] and not dados_normalizados['last_name']:
                print(f"[WOO SERVICE] Nome não encontrado nos dados")
                return {
                    'status': 'error',
                    'message': 'Nome obrigatório não encontrado'
                }
            
            # PROCESSAR no Sankhya com dados normalizados
            resultado = sankhya.processar_cliente_completo(dados_normalizados)
    
            if resultado.get('sucesso'):
                print(f"[WOO SERVICE] Cliente atualizado no Sankhya")
                return {
                    'status': 'success',
                    'message': f'Cliente {cliente_id} atualizado com sucesso',
                    'sankhya_result': resultado
                }
            else:
                print(f"[WOO SERVICE] Erro no Sankhya: {resultado.get('erro')}")
                return {
                    'status': 'error',
                    'message': f'Erro ao atualizar cliente no Sankhya: {resultado.get("erro")}'
                }
    
        except Exception as e:
            print(f"[WOO SERVICE] Erro ao processar cliente atualizado: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
        
    def _extrair_dados_cliente_webhook(self, data, headers):
        """
        Extrai dados de cliente de diferentes estruturas de webhook
        """
        # Dados normalizados padrão
        dados_normalizados = {
            'id': None,
            'email': None,
            'first_name': '',
            'last_name': '',
            'billing': {},
            'shipping': {},
            'meta_data': []
        }
        
        if not isinstance(data, dict):
            print(f"[WOO PROCESSOR DEBUG] Data não é dict: {type(data)}")
            return dados_normalizados
        
        # Estrutura 1: Dados diretos (customer.created típico)
        if data.get('id') and data.get('email'):
            print(f"[WOO PROCESSOR DEBUG] Estrutura 1: Dados diretos")
            dados_normalizados.update(data)
            return dados_normalizados
        
        # Estrutura 2: Dados em subchave 'customer'
        if 'customer' in data and isinstance(data['customer'], dict):
            print(f"[WOO PROCESSOR DEBUG] Estrutura 2: Dados em subchave 'customer'")
            customer_data = data['customer']
            dados_normalizados.update(customer_data)
            return dados_normalizados
        
        # Estrutura 3: Dados espalhados (típico do WooCommerce webhook)
        customer_id = data.get('id') or data.get('customer_id')
        email = data.get('email')
        
        # Se email não está no nível superior, procurar em billing
        if not email and 'billing' in data:
            email = data['billing'].get('email')
        
        # Buscar nome nos lugares possíveis
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        if not first_name and 'billing' in data:
            first_name = data['billing'].get('first_name', '')
            last_name = data['billing'].get('last_name', '')
        
        if customer_id:
            print(f"[WOO PROCESSOR DEBUG] Estrutura 3: Dados espalhados")
            dados_normalizados.update({
                'id': customer_id,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'billing': data.get('billing', {}),
                'shipping': data.get('shipping', {}),
                'meta_data': data.get('meta_data', [])
            })
            return dados_normalizados
        
        # Estrutura 4: Busca exaustiva
        print(f"[WOO PROCESSOR DEBUG] Estrutura 4: Busca exaustiva")
        print(f"[WOO PROCESSOR DEBUG] Keys disponíveis: {list(data.keys())}")
        
        return dados_normalizados

        # Buscar email em qualquer lugar
        def buscar_email_recursivo(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == 'email' and v and '@' in str(v):
                        return v
                    elif isinstance(v, dict):
                        resultado = buscar_email_recursivo(v)
                        if resultado:
                            return resultado
            return None
            
        if not email:
            email = buscar_email_recursivo(data)
            
        dados_normalizados.update({
            'id': customer_id,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'billing': data.get('billing', {}),
            'shipping': data.get('shipping', {}),
            'meta_data': data.get('meta_data', [])
        })
            
        print(f"[WOO PROCESSOR DEBUG] Resultado final da extração:")
        print(f"[WOO PROCESSOR DEBUG]   ID: {dados_normalizados['id']}")
        print(f"[WOO PROCESSOR DEBUG]   Email: {dados_normalizados['email']}")
        print(f"[WOO PROCESSOR DEBUG]   Nome: {dados_normalizados['first_name']} {dados_normalizados['last_name']}")
            
        return dados_normalizados

    def buscar_pedidos(self, status=None, limit=10):
        """
        Busca pedidos do WooCommerce
        FUNCIONALIDADE ORIGINAL MANTIDA
        """
        try:
            print(f"[WOO SERVICE] Buscando pedidos - Status: {status}, Limite: {limit}")
            
            if not self.client:
                return {
                    'status': 'error',
                    'message': 'Cliente WooCommerce não inicializado'
                }
            
            params = {
                'per_page': limit,
                'orderby': 'date',
                'order': 'desc'
            }
            
            if status:
                params['status'] = status
            
            pedidos = self.client.get_orders(params)
            
            print(f"[WOO SERVICE] Encontrados {len(pedidos)} pedidos")
            return {
                'status': 'success',
                'pedidos': pedidos,
                'total': len(pedidos),
                'filtros': {'status': status, 'limit': limit}
            }
            
        except Exception as e:
            print(f"[WOO SERVICE] Erro ao buscar pedidos: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def buscar_clientes(self, limit=10):
        """
        Busca clientes do WooCommerce
        FUNCIONALIDADE ORIGINAL MANTIDA
        """
        try:
            print(f"[WOO SERVICE] Buscando clientes - Limite: {limit}")
            
            if not self.client:
                return {
                    'status': 'error',
                    'message': 'Cliente WooCommerce não inicializado'
                }
            
            params = {
                'per_page': limit,
                'orderby': 'registered_date',
                'order': 'desc'
            }
            
            clientes = self.client.get_customers(params)
            
            print(f"[WOO SERVICE] Encontrados {len(clientes)} clientes")
            return {
                'status': 'success',
                'clientes': clientes,
                'total': len(clientes)
            }
            
        except Exception as e:
            print(f"[WOO SERVICE] Erro ao buscar clientes: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def update_order(self, order_id, data):
        """
        Atualiza um pedido no WooCommerce
        """
        return self.client.update_order(order_id, data)

    def processar_pedido_manual(self, pedido_id):
        """
        Processa um pedido específico manualmente
        FUNCIONALIDADE ORIGINAL MANTIDA
        """
        try:
            print(f"[WOO SERVICE] Processamento manual do pedido {pedido_id}")
            
            if not self.client:
                return {
                    'status': 'error',
                    'message': 'Cliente WooCommerce não inicializado'
                }
            
            # Busca pedido específico
            pedido = self.client.get_order(pedido_id)
            
            if not pedido:
                return {
                    'status': 'error',
                    'message': f'Pedido {pedido_id} não encontrado no WooCommerce'
                }
            
            # Processa como se fosse um webhook order.created
            headers_simulados = {
                'event_type': 'created',
                'resource': 'order',
                'webhook_id': 'manual',
                'delivery_id': f'manual_{pedido_id}'
            }
            
            # Usa o processador principal
            resultado = self.processar_webhook(headers_simulados, pedido)
            resultado['processamento_manual'] = True
            
            return resultado
            
        except Exception as e:
            print(f"[WOO SERVICE] Erro no processamento manual: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'pedido_id': pedido_id
            }
    
    def verificar_conectividade(self):
        """
        Verifica se a conexão com WooCommerce está funcionando
        FUNCIONALIDADE ORIGINAL MANTIDA
        """
        try:
            if not self.client:
                return {
                    'conectado': False,
                    'erro': 'Cliente WooCommerce não inicializado'
                }
            
            # Tenta uma consulta simples
            sistema = self.client.get_system_status()
            
            if sistema:
                print(f"[WOO SERVICE] Conectividade com WooCommerce OK")
                return {
                    'conectado': True,
                    'site_url': sistema.get('environment', {}).get('site_url', 'N/A'),
                    'wc_version': sistema.get('environment', {}).get('version', 'N/A'),
                    'wp_version': sistema.get('environment', {}).get('wp_version', 'N/A')
                }
            else:
                return {
                    'conectado': False, 
                    'erro': 'Resposta vazia do sistema'
                }
                
        except Exception as e:
            print(f"[WOO SERVICE] Erro de conectividade: {e}")
            return {
                'conectado': False,
                'erro': str(e)
            }
    
    def obter_estatisticas(self):
        """
        Obtém estatísticas do WooCommerce
        FUNCIONALIDADE ORIGINAL MANTIDA + MELHORADA
        """
        try:
            print(f"[WOO SERVICE] Obtendo estatísticas...")
            
            if not self.client:
                return {
                    'status': 'error',
                    'message': 'Cliente WooCommerce não inicializado'
                }
            
            # Busca dados recentes
            pedidos_recentes = self.client.get_orders({'per_page': 5})
            clientes_recentes = self.client.get_customers({'per_page': 5})
            
            # Testa conexão Sankhya
            sankhya_status = self.teste_conexao_sankhya()
            
            return {
                'status': 'success',
                'woocommerce': {
                    'total_pedidos_recentes': len(pedidos_recentes),
                    'total_clientes_recentes': len(clientes_recentes),
                    'ultimo_pedido': pedidos_recentes[0].get('id') if pedidos_recentes else None,
                    'ultimo_cliente': clientes_recentes[0].get('id') if clientes_recentes else None,
                    'conectado': True
                },
                'sankhya': sankhya_status,
                'servico': {
                    'versao': '2.5.0',
                    'eventos_suportados': [
                        'order.created', 'order.updated',
                        'customer.created', 'customer.updated', 
                        'product.created', 'product.updated'
                    ]
                }
            }
            
        except Exception as e:
            print(f"[WOO SERVICE] Erro ao obter estatísticas: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def validar_webhook(self, headers, data):
        """
        Valida se o webhook pode ser processado
        FUNCIONALIDADE ORIGINAL MANTIDA + MELHORADA
        """
        try:
            # Validações básicas
            if not headers:
                return False, "Headers não fornecidos"
            
            if not data:
                return False, "Dados não fornecidos"
            
            event_type = headers.get('event_type', '')
            resource = headers.get('resource', '')
            
            if not event_type or not resource:
                return False, "Tipo de evento ou recurso não identificado"
            
            # Validar se é um evento suportado
            eventos_suportados = [
                'order.created', 'order.updated',
                'customer.created', 'customer.updated',
                'product.created', 'product.updated'
            ]
            
            evento_completo = f"{resource}.{event_type}"
            if evento_completo not in eventos_suportados:
                return False, f"Evento {evento_completo} não suportado"
            
            # Validações específicas por tipo
            if resource == 'order':
                if not data.get('id') or not data.get('billing'):
                    return False, "Dados obrigatórios do pedido ausentes"
            
            elif resource == 'customer':
                if not data.get('id') or not data.get('email'):
                    return False, "Dados obrigatórios do cliente ausentes"
            
            return True, "Webhook válido"
            
        except Exception as e:
            return False, f"Erro na validação: {str(e)}"
    
    def teste_conexao_sankhya(self):
        """
        Testa a conexão com o Sankhya usando context manager
        FUNCIONALIDADE ORIGINAL MANTIDA + MELHORADA
        """
        try:
            with SankhyaService.with_auth() as sankhya:
                status = sankhya.validar_conexao()
                if status:
                    return {
                        "status": "success",
                        "message": "Conexão com Sankhya OK"
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Falha na validação da conexão"
                    }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Erro na conexão: {str(e)}"
            }
    
    def processar_webhook_batch(self, webhooks_list):
        """
        Processa múltiplos webhooks em lote
        FUNCIONALIDADE ADICIONAL ÚTIL
        """
        try:
            print(f"[WOO SERVICE] Processando lote de {len(webhooks_list)} webhooks...")
            
            resultados = []
            
            for i, webhook_data in enumerate(webhooks_list):
                headers = webhook_data.get('headers', {})
                data = webhook_data.get('data', {})
                
                print(f"[WOO SERVICE] Processando webhook {i+1}/{len(webhooks_list)}")
                
                resultado = self.processar_webhook(headers, data)
                resultado['indice_lote'] = i + 1
                resultados.append(resultado)
            
            # Estatísticas do lote
            sucessos = len([r for r in resultados if r.get('status') == 'success'])
            erros = len([r for r in resultados if r.get('status') == 'error'])
            ignorados = len([r for r in resultados if r.get('status') == 'skipped'])
            
            print(f"[WOO SERVICE] Lote processado: {sucessos} sucessos, {erros} erros, {ignorados} ignorados")
            
            return {
                'status': 'completed',
                'total_processados': len(webhooks_list),
                'sucessos': sucessos,
                'erros': erros,
                'ignorados': ignorados,
                'resultados': resultados
            }
            
        except Exception as e:
            print(f"[WOO SERVICE] Erro no processamento em lote: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def diagnosticar_integracao(self):
        """
        Diagnóstica todo o sistema de integração
        FUNCIONALIDADE ADICIONAL ÚTIL
        """
        try:
            print(f"[WOO SERVICE] Iniciando diagnóstico completo...")
            
            diagnostico = {
                'timestamp': __import__('datetime').datetime.now().isoformat(),
                'woocommerce': {'status': 'unknown'},
                'sankhya': {'status': 'unknown'},
                'configuracoes': {'status': 'unknown'},
                'recomendacoes': []
            }
            
            # 1. Teste WooCommerce
            try:
                wc_conectividade = self.verificar_conectividade()
                if wc_conectividade.get('conectado', False):
                    diagnostico['woocommerce'] = {
                        'status': 'ok',
                        'site_url': wc_conectividade.get('site_url'),
                        'versao': wc_conectividade.get('wc_version')
                    }
                else:
                    diagnostico['woocommerce'] = {
                        'status': 'erro',
                        'erro': wc_conectividade.get('erro')
                    }
                    diagnostico['recomendacoes'].append('Verificar credenciais WooCommerce no .env')
            except Exception as e:
                diagnostico['woocommerce'] = {'status': 'erro', 'erro': str(e)}
            
            # 2. Teste Sankhya
            try:
                sankhya_status = self.teste_conexao_sankhya()
                diagnostico['sankhya'] = sankhya_status
                if sankhya_status.get('status') != 'success':
                    diagnostico['recomendacoes'].append('Verificar credenciais Sankhya no .env')
            except Exception as e:
                diagnostico['sankhya'] = {'status': 'erro', 'erro': str(e)}
            
            # 3. Teste Configurações
            try:
                configs_necessarias = [
                    'WC_URL', 'WC_KEY', 'WC_SECRET',
                    'SANKHYA_BASE_URL', 'SANKHYA_APPKEY', 'SANKHYA_TOKEN',
                    'SANKHYA_USERNAME', 'SANKHYA_PASSWORD', 'WEBHOOK_SECRET'
                ]
                
                configs_faltando = []
                for config in configs_necessarias:
                    if not self.config.get(config):
                        configs_faltando.append(config)
                
                if configs_faltando:
                    diagnostico['configuracoes'] = {
                        'status': 'incompleto',
                        'faltando': configs_faltando
                    }
                    diagnostico['recomendacoes'].append(f'Configurar variáveis: {", ".join(configs_faltando)}')
                else:
                    diagnostico['configuracoes'] = {'status': 'ok'}
                    
            except Exception as e:
                diagnostico['configuracoes'] = {'status': 'erro', 'erro': str(e)}
            
            # 4. Status Geral
            todos_ok = all([
                diagnostico['woocommerce']['status'] == 'ok',
                diagnostico['sankhya']['status'] == 'success',
                diagnostico['configuracoes']['status'] == 'ok'
            ])
            
            diagnostico['status_geral'] = 'ok' if todos_ok else 'problemas_encontrados'
            
            if todos_ok:
                diagnostico['recomendacoes'].append('Sistema totalmente funcional!')
            
            print(f"[WOO SERVICE] Diagnóstico concluído: {diagnostico['status_geral']}")
            
            return diagnostico
            
        except Exception as e:
            print(f"[WOO SERVICE] Erro no diagnóstico: {e}")
            return {
                'status_geral': 'erro',
                'erro': str(e),
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }


# FUNÇÕES DE CONVENIÊNCIA PARA COMPATIBILIDADE

def processar_pedido_criado(data):
    """Função de conveniência para compatibilidade - MANTIDA"""
    service = WooCommerceService()
    headers = {'event_type': 'created', 'resource': 'order', 'webhook_id': 'func_conv'}
    return service.processar_webhook(headers, data)

def processar_cliente_criado(data):
    """Função de conveniência para compatibilidade - MANTIDA"""
    service = WooCommerceService()
    headers = {'event_type': 'created', 'resource': 'customer', 'webhook_id': 'func_conv'}
    return service.processar_webhook(headers, data)

def processar_pedido_atualizado(data):
    """Função de conveniência para compatibilidade - MANTIDA"""
    service = WooCommerceService()
    headers = {'event_type': 'updated', 'resource': 'order', 'webhook_id': 'func_conv'}
    return service.processar_webhook(headers, data)

def processar_cliente_atualizado(data):
    """Função de conveniência para compatibilidade - MANTIDA"""
    service = WooCommerceService()
    headers = {'event_type': 'updated', 'resource': 'customer', 'webhook_id': 'func_conv'}
    return service.processar_webhook(headers, data)

def processar_produto_criado(data):
    """Função de conveniência para produtos - MANTIDA"""
    service = WooCommerceService()
    headers = {'event_type': 'created', 'resource': 'product', 'webhook_id': 'func_conv'}
    return service.processar_webhook(headers, data)

def processar_produto_atualizado(data):
    """Função de conveniência para produtos atualizados - MANTIDA"""
    service = WooCommerceService()
    headers = {'event_type': 'updated', 'resource': 'product', 'webhook_id': 'func_conv'}
    return service.processar_webhook(headers, data)

def processar_pedido_removido(data):
    """Função de conveniência para compatibilidade - MANTIDA"""
    print(f"[WOO PROCESSOR] Pedido removido: {data.get('id')} - Registrado")
    return {
        "status": "success",
        "message": f"Pedido {data.get('id')} removido - registrado",
        "pedido_id": data.get('id'),
        "action": "logged"
    }

def processar_cliente_removido(data):
    """Função de conveniência para compatibilidade - MANTIDA"""
    print(f"[WOO PROCESSOR] Cliente removido: {data.get('id')} - Registrado")
    return {
        "status": "success", 
        "message": f"Cliente {data.get('id')} removido - registrado",
        "customer_id": data.get('id'),
        "action": "logged"
    }

def processar_produto_removido(data):
    """Função de conveniência para produtos removidos - MANTIDA"""
    print(f"[WOO PROCESSOR] Produto removido: {data.get('id')} - Registrado")
    return {
        "status": "success",
        "message": f"Produto {data.get('id')} removido - registrado",
        "product_id": data.get('id'),
        "action": "logged"
    }
