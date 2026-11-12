from utils.normalize import limpar_documento, validar_telefone
from datetime import datetime

class WooCommerceMapper:
    """
    Mapeador de dados entre WooCommerce e Sankhya
    """
    
    @staticmethod
    def mapear_cliente_para_sankhya(data_woo):
        """
        Mapeia dados de cliente do WooCommerce para formato Sankhya
        """
        billing = data_woo.get('billing', {})
        
        # Nome
        first_name = data_woo.get('first_name', '') or billing.get('first_name', '')
        last_name = data_woo.get('last_name', '') or billing.get('last_name', '')
        nome_completo = f"{first_name} {last_name}".strip()
        
        # Contato
        email = data_woo.get('email', '') or billing.get('email', '')
        telefone = data_woo.get('phone', '') or billing.get('phone', '') or billing.get('cellphone', '')
        telefone_limpo = validar_telefone(telefone) if telefone else ""
        
        # Documento
        documento = billing.get('cpf', '') or billing.get('cnpj', '')
        if not documento:
            for meta in data_woo.get('meta_data', []):
                key = meta.get('key', '')
                value = meta.get('value', '')
                if key in ['_billing_cpf', '_billing_cnpj', 'cpf', 'cnpj'] and value:
                    documento = value
                    break
        
        documento_limpo = limpar_documento(documento) if documento else ""
        
        # CÓDIGO IBGE (NOVO)
        ibge_code = ''
        for meta in data_woo.get('meta_data', []):
            key = meta.get('key', '')
            value = meta.get('value', '')
            if key == 'billing_ibge_code' and value:
                ibge_code = value
                break
        
        # Tipo de pessoa
        tipo_pessoa = "F"  # Padrão: Pessoa Física
        persontype = billing.get('persontype', '')
        if persontype == 'J' or (documento_limpo and len(documento_limpo) == 14):
            tipo_pessoa = "J"
        
        # ENDEREÇO (MODIFICADO)
        endereco = {
            'logradouro': billing.get('address_1', ''),
            'numero': billing.get('number', ''),
            'complemento': billing.get('address_2', ''),
            'bairro': billing.get('neighborhood', '') or billing.get('city', ''),
            'cidade': billing.get('city', ''),
            'estado': billing.get('state', ''),
            'cep': billing.get('postcode', ''),
            'pais': billing.get('country', 'BR'),
            'ibge_code': ibge_code  # NOVO
        }
        
        return {
            'nome': nome_completo,
            'email': email,
            'telefone': telefone_limpo,
            'documento': documento_limpo,
            'tipo_pessoa': tipo_pessoa,
            'endereco': endereco,
            'dados_originais': data_woo
        }    
    @staticmethod
    def mapear_pedido_para_sankhya(data_woo):
        """
        Mapeia dados de pedido do WooCommerce para formato Sankhya
        """
        # Data do pedido
        date_created = data_woo.get('date_created', '')
        data_pedido = datetime.now().strftime("%d/%m/%Y")
        
        if date_created:
            try:
                # Tenta parsear ISO format
                dt = datetime.fromisoformat(date_created.replace('Z', '+00:00'))
                data_pedido = dt.strftime("%d/%m/%Y")
            except:
                # Se falhar, usa data atual
                pass
        
        # Cliente
        cliente_dados = WooCommerceMapper.mapear_cliente_para_sankhya({
            'billing': data_woo.get('billing', {}),
            'meta_data': data_woo.get('meta_data', [])
        })
        
        # Itens do pedido
        itens = []
        for item_woo in data_woo.get('line_items', []):
            # Código do produto: prioriza SKU, senão usa product_id
            sku = item_woo.get('sku', '')
            product_id = item_woo.get('product_id', 0)
            codigo_produto = sku if sku else str(product_id)
            
            item_sankhya = {
                'codigo_produto': codigo_produto,
                'quantidade': float(item_woo.get('quantity', 1)),
                'valor_unitario': float(item_woo.get('price', 0)),
                'descricao': item_woo.get('name', ''),
                'dados_originais': item_woo
            }
            itens.append(item_sankhya)
        
        # Valores do pedido
        valores = {
            'subtotal': float(data_woo.get('subtotal', 0)),
            'total_desconto': float(data_woo.get('discount_total', 0)),
            'total_frete': float(data_woo.get('shipping_total', 0)),
            'total_impostos': float(data_woo.get('tax_total', 0)),
            'total_geral': float(data_woo.get('total', 0))
        }
        
        # Método de pagamento
        payment_method = data_woo.get('payment_method', '')
        payment_title = data_woo.get('payment_method_title', '')
        
        return {
            'id_woo': data_woo.get('id'),
            'numero_pedido': data_woo.get('number', ''),
            'data_pedido': data_pedido,
            'status': data_woo.get('status', ''),
            'cliente': cliente_dados,
            'itens': itens,
            'valores': valores,
            'pagamento': {
                'metodo': payment_method,
                'titulo': payment_title
            },
            'observacoes': data_woo.get('customer_note', ''),
            'dados_originais': data_woo
        }
    
    @staticmethod
    def mapear_produto_para_sankhya(data_woo):
        """
        Mapeia dados de produto do WooCommerce para formato Sankhya
        """
        # Preços
        regular_price = float(data_woo.get('regular_price', 0))
        sale_price = float(data_woo.get('sale_price', 0))
        preco_venda = sale_price if sale_price > 0 else regular_price
        
        # Estoque
        manage_stock = data_woo.get('manage_stock', False)
        stock_quantity = int(data_woo.get('stock_quantity', 0)) if manage_stock else 0
        
        # Dimensões e peso
        dimensions = data_woo.get('dimensions', {})
        peso = float(data_woo.get('weight', 0))
        
        return {
            'id_woo': data_woo.get('id'),
            'sku': data_woo.get('sku', ''),
            'nome': data_woo.get('name', ''),
            'descricao': data_woo.get('description', ''),
            'descricao_curta': data_woo.get('short_description', ''),
            'preco_regular': regular_price,
            'preco_promocional': sale_price,
            'preco_venda': preco_venda,
            'gerencia_estoque': manage_stock,
            'quantidade_estoque': stock_quantity,
            'peso': peso,
            'dimensoes': {
                'comprimento': float(dimensions.get('length', 0)),
                'largura': float(dimensions.get('width', 0)),
                'altura': float(dimensions.get('height', 0))
            },
            'status': data_woo.get('status', 'draft'),
            'categoria_ids': [cat.get('id') for cat in data_woo.get('categories', [])],
            'dados_originais': data_woo
        }
    
    @staticmethod
    def mapear_endereco_entrega(data_woo):
        """
        Mapeia dados de endereço de entrega
        """
        shipping = data_woo.get('shipping', {})
        
        if not shipping:
            # Se não tem dados de entrega, usa dados de cobrança
            shipping = data_woo.get('billing', {})
        
        return {
            'nome': f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}".strip(),
            'empresa': shipping.get('company', ''),
            'logradouro': shipping.get('address_1', ''),
            'numero': shipping.get('number', ''),
            'complemento': shipping.get('address_2', ''),
            'bairro': shipping.get('neighborhood', '') or shipping.get('city', ''),
            'cidade': shipping.get('city', ''),
            'estado': shipping.get('state', ''),
            'cep': shipping.get('postcode', ''),
            'pais': shipping.get('country', 'BR')
        }
    
    @staticmethod
    def extrair_meta_data(data_woo, chave):
        """
        Extrai valor específico do meta_data
        Útil para buscar dados do AutoCEP e outros plugins
        """
        meta_data = data_woo.get('meta_data', [])
        for meta in meta_data:
            if meta.get('key') == chave:
                value = meta.get('value', '')
                return value if value else ''
        return ''
    
    @staticmethod
    def extrair_codigo_ibge(data_woo):
        """
        Método específico para extrair código IBGE do AutoCEP
        """
        return WooCommerceMapper.extrair_meta_data(data_woo, 'billing_ibge_code')
    
    @staticmethod
    def mapear_status_pedido_sankhya(status_woo):
        """
        Mapeia status do WooCommerce para Sankhya
        """
        mapeamento = {
            'pending': 'PENDENTE',
            'processing': 'EM_PROCESSAMENTO', 
            'on-hold': 'EM_ESPERA',
            'completed': 'CONCLUIDO',
            'cancelled': 'CANCELADO',
            'refunded': 'REEMBOLSADO',
            'failed': 'FALHOU'
        }
        return mapeamento.get(status_woo, 'PENDENTE')
