"""
WooCommerce Validators - VERSÃO CORRIGIDA
Remove importação circular que estava causando erro na inicialização
"""

from utils.normalize import validar_email, validar_telefone, limpar_documento

class WooCommerceValidator:
    """
    Validadores para dados do WooCommerce - VERSÃO CORRIGIDA
    """
    
    @staticmethod
    def validar_pedido(data):
        """
        Valida estrutura de dados de pedido
        """
        erros = []
        
        # Campos obrigatórios
        if not data.get('id'):
            erros.append("ID do pedido não informado")
        
        if not data.get('billing'):
            erros.append("Dados de cobrança não informados")
        else:
            billing = data.get('billing')
            if not billing.get('first_name') and not billing.get('last_name'):
                erros.append("Nome do cliente não informado")
        
        # Itens do pedido
        line_items = data.get('line_items', [])
        if not line_items:
            erros.append("Pedido sem itens")
        else:
            for i, item in enumerate(line_items):
                if not item.get('product_id') and not item.get('sku'):
                    erros.append(f"Item {i+1}: Produto não identificado (sem product_id nem SKU)")
                
                if not item.get('quantity') or item.get('quantity') <= 0:
                    erros.append(f"Item {i+1}: Quantidade inválida")
        
        return erros
    
    @staticmethod
    def validar_cliente(data):
        """
        Valida estrutura de dados de cliente
        """
        erros = []
        
        # Campos obrigatórios
        if not data.get('email'):
            erros.append("E-mail do cliente não informado")
        else:
            if not validar_email(data.get('email')):
                erros.append("E-mail inválido")
        
        # Validação de telefone (se informado)
        telefone = data.get('phone', '') or data.get('billing', {}).get('phone', '')
        if telefone and not validar_telefone(telefone):
            erros.append("Telefone inválido")
        
        # Validação de documento (se informado)
        billing = data.get('billing', {})
        documento = billing.get('cpf', '') or billing.get('cnpj', '')
        
        if not documento:
            # Procura nos meta_data
            for meta in data.get('meta_data', []):
                key = meta.get('key', '')
                value = meta.get('value', '')
                if key in ['_billing_cpf', '_billing_cnpj', 'cpf', 'cnpj'] and value:
                    documento = value
                    break
        
        if documento:
            documento_limpo = limpar_documento(documento)
            if documento_limpo and len(documento_limpo) not in [11, 14]:
                erros.append("Documento (CPF/CNPJ) inválido")
        
        return erros
    
    @staticmethod
    def validar_produto(data):
        """
        Valida estrutura de dados de produto
        """
        erros = []
        
        if not data.get('id'):
            erros.append("ID do produto não informado")
        
        if not data.get('name'):
            erros.append("Nome do produto não informado")
        
        # SKU é importante para integração
        if not data.get('sku'):
            erros.append("SKU do produto não informado (recomendado para integração)")
        
        return erros
    
    @staticmethod
    def extrair_dados_cliente_de_pedido(data_pedido):
        """
        Extrai dados de cliente de um pedido para validação
        """
        billing = data_pedido.get('billing', {})
        
        dados_cliente = {
            'id': data_pedido.get('customer_id', 0),
            'first_name': billing.get('first_name', ''),
            'last_name': billing.get('last_name', ''),
            'email': billing.get('email', ''),
            'phone': billing.get('phone', ''),
            'billing': billing,
            'meta_data': data_pedido.get('meta_data', [])
        }
        
        return dados_cliente
    
    @staticmethod
    def validar_webhook_headers(headers):
        """
        Valida headers necessários do webhook
        """
        erros = []
        
        # Headers obrigatórios mínimos
        required_headers = ['event_type', 'resource']
        
        for header in required_headers:
            if not headers.get(header):
                erros.append(f"Header '{header}' não encontrado ou vazio")
        
        # Validações adicionais se os headers básicos existem
        event_type = headers.get('event_type')
        resource = headers.get('resource')
        
        if event_type and event_type not in ['created', 'updated', 'deleted', 'restored']:
            erros.append(f"Event type '{event_type}' não suportado")
        
        if resource and resource not in ['order', 'customer', 'product', 'coupon']:
            erros.append(f"Resource '{resource}' não suportado")
        
        # Headers opcionais mas importantes para logging
        optional_headers = ['webhook_id', 'delivery_id']
        for header in optional_headers:
            if not headers.get(header):
                # Log warning mas não adiciona como erro
                print(f"[WEBHOOK VALIDATOR] Warning: Header '{header}' não fornecido")
        
        return erros
    
    @staticmethod
    def normalizar_evento(event_type, resource):
        """
        Normaliza nome do evento para padronização
        """
        if not event_type or not resource:
            print(f"[WOOCOMMERCE VALIDATOR] Erro: event_type='{event_type}', resource='{resource}'")
            return None
        
        evento_normalizado = f"{resource.lower()}.{event_type.lower()}"
        print(f"[WOOCOMMERCE VALIDATOR] Evento normalizado: {evento_normalizado}")
        return evento_normalizado
    
    @staticmethod
    def eh_evento_suportado(event_type, resource):
        """
        Verifica se o evento é suportado pela integração
        """
        eventos_suportados = {
            'order.created',
            'order.updated', 
            'order.deleted',
            'customer.created',
            'customer.updated',
            'customer.deleted',
            'product.created',
            'product.updated',
            'product.deleted'
        }
        
        evento_normalizado = WooCommerceValidator.normalizar_evento(event_type, resource)
        eh_suportado = evento_normalizado in eventos_suportados
        
        print(f"[WOOCOMMERCE VALIDATOR] Evento '{evento_normalizado}' suportado: {eh_suportado}")
        return eh_suportado