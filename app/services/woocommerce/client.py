import requests
import os
from config.settings import load_config

class WooCommerceClientDefensive:
    """
    Cliente WooCommerce DEFENSIVO - Detecta e corrige configurações trocadas
    VERSÃO APRIMORADA: Corrige problema de barra dupla nos logs
    """
    
    def __init__(self):
        self.config = load_config()
        self.base_url = None
        self.consumer_key = None
        self.consumer_secret = None
        
        # INICIALIZAÇÃO DEFENSIVA
        self._inicializar_configuracoes_defensivas()
        
        if not all([self.base_url, self.consumer_key, self.consumer_secret]):
            raise ValueError("Não foi possível corrigir as configurações do WooCommerce")
            
        # Normaliza URL
        self.base_url = self._normalizar_url_base(self.base_url)
        print(f"[WOO CLIENT] Configuração corrigida e validada")
    
    def _inicializar_configuracoes_defensivas(self):
        """
        Detecta e corrige configurações trocadas
        """
        print(f"[WOO CLIENT] Inicialização defensiva...")
        
        # Obtém todas as configurações brutas
        config_raw = {
            'WC_URL': os.getenv('WC_URL', ''),
            'WC_KEY': os.getenv('WC_KEY', ''),
            'WC_SECRET': os.getenv('WC_SECRET', ''),
            # Também verifica outras variáveis caso tenham sido trocadas
            'WEBHOOK_SECRET': os.getenv('WEBHOOK_SECRET', ''),
            'SANKHYA_BASE_URL': os.getenv('SANKHYA_BASE_URL', ''),
            'SANKHYA_USERNAME': os.getenv('SANKHYA_USERNAME', ''),
        }
        
        print(f"[WOO CLIENT] Analisando configurações...")
        for key, value in config_raw.items():
            if value:
                print(f"[WOO CLIENT]   {key}: definido")
        
        # DETECÇÃO INTELIGENTE
        url_candidatos = []
        key_candidatos = []
        secret_candidatos = []
        
        # Busca URLs (começam com http)
        for key, value in config_raw.items():
            if value.startswith('http'):
                url_candidatos.append((key, value))
                print(f"[WOO CLIENT] URL encontrada em {key}: {value}")
        
        # Busca Consumer Keys (começam com ck_)
        for key, value in config_raw.items():
            if value.startswith('ck_'):
                key_candidatos.append((key, value))
                print(f"[WOO CLIENT] Consumer Key encontrada em {key}: {value[:20]}...")
        
        # Busca Consumer Secrets (começam com cs_)
        for key, value in config_raw.items():
            if value.startswith('cs_'):
                secret_candidatos.append((key, value))
                print(f"[WOO CLIENT] Consumer Secret encontrada em {key}: {value[:20]}...")
        
        # CORREÇÃO AUTOMÁTICA
        
        # 1. URL
        if url_candidatos:
            self.base_url = url_candidatos[0][1]  # Pega a primeira URL encontrada
            if url_candidatos[0][0] != 'WC_URL':
                print(f"[WOO CLIENT] URL corrigida automaticamente de {url_candidatos[0][0]}")
        else:
            print(f"[WOO CLIENT] Nenhuma URL válida encontrada")
            self.base_url = None
        
        # 2. Consumer Key
        if key_candidatos:
            self.consumer_key = key_candidatos[0][1]  # Pega a primeira key encontrada
            if key_candidatos[0][0] != 'WC_KEY':
                print(f"[WOO CLIENT] Consumer Key corrigida automaticamente de {key_candidatos[0][0]}")
        else:
            print(f"[WOO CLIENT] Nenhuma Consumer Key válida encontrada")
            self.consumer_key = None
        
        # 3. Consumer Secret
        if secret_candidatos:
            self.consumer_secret = secret_candidatos[0][1]  # Pega o primeiro secret encontrado
            if secret_candidatos[0][0] != 'WC_SECRET':
                print(f"[WOO CLIENT] Consumer Secret corrigida automaticamente de {secret_candidatos[0][0]}")
        else:
            print(f"[WOO CLIENT] Nenhuma Consumer Secret válida encontrada")
            self.consumer_secret = None
        
        # RELATÓRIO DA CORREÇÃO
        print(f"[WOO CLIENT] Configuração final:")
        print(f"[WOO CLIENT]   URL: {self.base_url}")
        print(f"[WOO CLIENT]   Key: {'definido' if self.consumer_key else 'N/A'}")
        print(f"[WOO CLIENT]   Secret: {'definido' if self.consumer_secret else 'N/A'}")
        
        # GUIA DE CORREÇÃO MANUAL (se necessário)
        if not all([self.base_url, self.consumer_key, self.consumer_secret]):
            print(f"[WOO CLIENT] CORREÇÃO MANUAL NECESSÁRIA:")
            print(f"[WOO CLIENT] Adicione no seu arquivo .env:")
            print(f"[WOO CLIENT]")
            
            if not self.base_url:
                print(f"[WOO CLIENT] WC_URL=https://cliente8.example.com  # URL do seu WooCommerce")
            if not self.consumer_key:
                print(f"[WOO CLIENT] WC_KEY=ck_xxxxxxxxxxxxxxx  # Consumer Key (ck_)")
            if not self.consumer_secret:
                print(f"[WOO CLIENT] WC_SECRET=cs_xxxxxxxxxxxxxxx  # Consumer Secret (cs_)")
            
            print(f"[WOO CLIENT]")
    
    def _normalizar_url_base(self, url):
        """
        Normaliza URL base (versão defensiva e corrigida)
        """
        if not url:
            raise ValueError("URL do WooCommerce não configurada")
        
        # Remove barra final se existir
        url = url.rstrip('/')
        
        # Valida se é uma URL válida
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError(f"URL deve começar com http:// ou https://: {url}")
        
        # Garante que termina com /wp-json/wc/v3
        if not url.endswith('/wp-json/wc/v3'):
            if '/wp-json/wc/v3' in url:
                # URL já tem o path, apenas normaliza
                parts = url.split('/wp-json/wc/v3')
                url = parts[0] + '/wp-json/wc/v3'
            else:
                # Adiciona o path da API
                url = url + '/wp-json/wc/v3'
        
        print(f"[WOO CLIENT] URL normalizada: {url}")
        return url
    
    def get_auth(self):
        """
        Retorna tupla para autenticação básica
        """
        return (self.consumer_key, self.consumer_secret)
    
    def get_url(self, endpoint):
        """
        Constrói URL completa para endpoint - VERSÃO CORRIGIDA
        Evita barras duplas que causavam erro 404
        """
        # Remove barras iniciais do endpoint
        endpoint = endpoint.lstrip('/')
        
        # Garante que base_url não termine com barra
        base_clean = self.base_url.rstrip('/')
        
        # Constrói URL final
        full_url = f"{base_clean}/{endpoint}"
        
        # Debug: Log da URL construída (apenas para desenvolvimento)
        # print(f"[WOO CLIENT DEBUG] URL construída: {full_url}")
        
        return full_url
    
    def _fazer_requisicao(self, method, endpoint, data=None, params=None):
        """
        Método genérico para fazer requisições - VERSÃO APRIMORADA
        """
        url = self.get_url(endpoint)
        
        try:
            print(f"[WOO CLIENT] {method.upper()} {endpoint}")
            
            kwargs = {
                'auth': self.get_auth(),
                'timeout': 30,
                'headers': {
                    'User-Agent': 'WooCommerce-Sankhya-Integration/2.0',
                    'Accept': 'application/json'
                }
            }
            
            if params:
                kwargs['params'] = params
            
            if data:
                kwargs['json'] = data
                kwargs['headers']['Content-Type'] = 'application/json'
            
            # Faz a requisição
            if method.upper() == 'GET':
                response = requests.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, **kwargs)
            elif method.upper() == 'PUT':
                response = requests.put(url, **kwargs)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
            print(f"[WOO CLIENT] {method.upper()} {endpoint} - Status: {response.status_code}")
            
            if response.status_code >= 400:
                print(f"[WOO CLIENT] Erro HTTP {response.status_code}")
                print(f"[WOO CLIENT] URL utilizada: {url}")
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', 'Erro desconhecido')
                    print(f"[WOO CLIENT] Erro: {error_msg}")
                except:
                    print(f"[WOO CLIENT] Response: {response.text[:200]}")
                
                response.raise_for_status()
            
            try:
                return response.json()
            except ValueError:
                print(f"[WOO CLIENT] Resposta não é JSON válido")
                return {"error": "Resposta inválida", "raw_response": response.text}
            
        except Exception as e:
            print(f"[WOO CLIENT] Erro na requisição: {e}")
            print(f"[WOO CLIENT] URL: {url}")
            raise
    
    def get_request(self, endpoint, params=None):
        """Faz requisição GET"""
        return self._fazer_requisicao('GET', endpoint, params=params)
    
    def post_request(self, endpoint, data):
        """Faz requisição POST"""
        return self._fazer_requisicao('POST', endpoint, data=data)
    
    def get_orders(self, params=None):
        """
        Busca pedidos do WooCommerce
        """
        if params is None:
            params = {}
        
        # Parmetros padrão
        default_params = {
            'per_page': 10,
            'orderby': 'date',
            'order': 'desc'
        }
        
        # Mescla parmetros
        final_params = {**default_params, **params}
        
        try:
            print(f"[WOO CLIENT] Buscando pedidos com parmetros: {final_params}")
            return self.get_request('orders', final_params)
        except Exception as e:
            print(f"[WOO CLIENT] Erro ao buscar pedidos: {e}")
            raise
    
    def get_order(self, order_id):
        """
        Busca pedido específico
        """
        try:
            print(f"[WOO CLIENT] Buscando pedido {order_id}")
            return self.get_request(f'orders/{order_id}')
        except Exception as e:
            print(f"[WOO CLIENT] Erro ao buscar pedido {order_id}: {e}")
            raise
    
    def get_customers(self, params=None):
        """
        Busca clientes do WooCommerce
        """
        if params is None:
            params = {}
        
        # Parmetros padrão
        default_params = {
            'per_page': 10,
            'orderby': 'registered_date',
            'order': 'desc'
        }
        
        # Mescla parmetros
        final_params = {**default_params, **params}
        
        try:
            print(f"[WOO CLIENT] Buscando clientes com parmetros: {final_params}")
            return self.get_request('customers', final_params)
        except Exception as e:
            print(f"[WOO CLIENT] Erro ao buscar clientes: {e}")
            raise
    
    def get_customer(self, customer_id):
        """
        Busca cliente específico
        """
        try:
            print(f"[WOO CLIENT] Buscando cliente {customer_id}")
            return self.get_request(f'customers/{customer_id}')
        except Exception as e:
            print(f"[WOO CLIENT] Erro ao buscar cliente {customer_id}: {e}")
            raise
    
    def get_system_status(self):
        """
        Busca status do sistema WooCommerce
        """
        try:
            print(f"[WOO CLIENT] Verificando status do sistema")
            return self.get_request('system_status')
        except Exception as e:
            print(f"[WOO CLIENT] Erro ao verificar status: {e}")
            return None
    
    def add_order_note(self, order_id, note, customer_note=False):
        """
        Adiciona nota ao pedido - VERSÃO APRIMORADA
        """
        if not order_id or not note:
            print(f"[WOO CLIENT] Order ID ou nota inválidos")
            return None
        
        try:
            order_id = int(order_id)
        except (ValueError, TypeError):
            print(f"[WOO CLIENT] Order ID inválido: {order_id}")
            return None
        
        data = {
            "note": str(note)[:1000],  # Limita a 1000 caracteres
            "customer_note": bool(customer_note)
        }
        
        try:
            print(f"[WOO CLIENT] Adicionando nota ao pedido {order_id}")
            result = self.post_request(f"orders/{order_id}/notes", data)
            print(f"[WOO CLIENT] Nota adicionada com sucesso")
            return result
        except Exception as e:
            print(f"[WOO CLIENT] Erro ao adicionar nota: {e}")
            return None
    
    def update_order(self, order_id, data):
        """
        Atualiza um pedido no WooCommerce via PUT
        """
        try:
            order_id = int(order_id)
            result = self._fazer_requisicao('PUT', f"orders/{order_id}", data=data)
            print(f"[WOO CLIENT] Pedido {order_id} atualizado")
            return result
        except Exception as e:
            print(f"[WOO CLIENT] Erro ao atualizar pedido {order_id}: {e}")
            return None

    def test_connection(self):
        """
        Testa conexão com a API - VERSÃO APRIMORADA
        """
        try:
            print(f"[WOO CLIENT] Testando conexão...")
            
            endpoints_teste = ["products?per_page=1", "orders?per_page=1", "customers?per_page=1"]
            
            for endpoint in endpoints_teste:
                try:
                    print(f"[WOO CLIENT] Testando endpoint: {endpoint}")
                    result = self.get_request(endpoint)
                    if result and not result.get('error'):
                        print(f"[WOO CLIENT] Conexão OK via {endpoint}")
                        return True
                except Exception as e:
                    print(f"[WOO CLIENT] Falha no endpoint {endpoint}: {e}")
                    continue
            
            print(f"[WOO CLIENT] Falha em todos os endpoints testados")
            return False
            
        except Exception as e:
            print(f"[WOO CLIENT] Erro no teste: {e}")
            return False

# Aliás para compatibilidade
WooCommerceClient = WooCommerceClientDefensive