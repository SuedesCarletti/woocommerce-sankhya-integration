from .base import SankhyaClient

class TransportadorasService(SankhyaClient):
    """
    NOVO SERVIÇO: Gestão de transportadoras no Sankhya
    Consulta transportadoras por ID AllPost do WooCommerce
    """
    
    def consultar_por_id_allpost(self, id_allpost):
        """
        Consulta transportadora usando o campo AD_IDALLPOST
        """
        if not id_allpost:
            return None
            
        print(f"[TRANSPORTADORAS] Consultando ID AllPost: {id_allpost}")
        
        criteria = {
            "expression": {
                "$": "this.AD_IDALLPOST = ?"
            },
            "parameter": [
                {
                    "$": str(id_allpost),
                    "type": "S"
                }
            ]
        }
        
        try:
            result = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,AD_IDALLPOST,FORNECEDOR,ATIVO",
                criteria=criteria
            )
            
            entities = result.get('responseBody', {}).get('entities', {})
            total = int(entities.get('total', '0'))
            
            print(f"[TRANSPORTADORAS] Encontrados: {total} registros")
            
            if total == 0:
                print(f"[TRANSPORTADORAS] AD_IDALLPOST {id_allpost} não encontrado")
                return None
            
            entity = entities.get('entity')
            if isinstance(entity, list):
                entity = entity[0]
            
            # Extrai dados usando estrutura f0, f1, f2...
            transportadora = {
                'CODPARC': self._extract_value(entity.get('f0')),
                'NOMEPARC': self._extract_value(entity.get('f1')),
                'AD_IDALLPOST': self._extract_value(entity.get('f2')),
                'FORNECEDOR': self._extract_value(entity.get('f3')),
                'ATIVO': self._extract_value(entity.get('f4'))
            }
            
            print(f"[TRANSPORTADORAS] Encontrada: {transportadora['NOMEPARC']} (CODPARC: {transportadora['CODPARC']})")
            return transportadora
            
        except Exception as e:
            print(f"[TRANSPORTADORAS] Erro ao consultar ID AllPost {id_allpost}: {e}")
            return None
    
    def _extract_value(self, field_obj):
        """Extrai valor do objeto de campo do Sankhya"""
        if not field_obj:
            return ""
        
        if isinstance(field_obj, dict):
            return field_obj.get('$', '')
        
        return str(field_obj)
    
    def processar_shipping_woocommerce(self, shipping_lines):
        """
        Processa dados de shipping do WooCommerce e encontra transportadora
        """
        if not shipping_lines or not isinstance(shipping_lines, list):
            print(f"[TRANSPORTADORAS] Nenhuma linha de shipping encontrada")
            return None
        
        for shipping_line in shipping_lines:
            meta_data = shipping_line.get('meta_data', [])
            
            for meta in meta_data:
                key = meta.get('key', '')
                value = meta.get('value', '')
                
                if key == 'allpost_transportadora_id' and value:
                    print(f"[TRANSPORTADORAS] ID AllPost encontrado: {value}")
                    
                    transportadora = self.consultar_por_id_allpost(value)
                    
                    if transportadora:
                        # Adiciona informações do shipping
                        transportadora['shipping_info'] = {
                            'method_title': shipping_line.get('method_title', ''),
                            'total': shipping_line.get('total', '0'),
                            'delivery_time': self._extrair_prazo_entrega(meta_data),
                            'metodo': self._extrair_metodo_transporte(meta_data)
                        }
                        
                        print(f"[TRANSPORTADORAS] Shipping processado:")
                        print(f"[TRANSPORTADORAS]   CODPARC: {transportadora['CODPARC']}")
                        print(f"[TRANSPORTADORAS]   Nome: {transportadora['NOMEPARC']}")
                        print(f"[TRANSPORTADORAS]   Valor: R$ {transportadora['shipping_info']['total']}")
                        
                        return transportadora
                    else:
                        print(f"[TRANSPORTADORAS] ID AllPost {value} não encontrado")
        
        print(f"[TRANSPORTADORAS] Nenhum ID AllPost encontrado no shipping")
        return None
    
    def obter_transportadora_padrao(self):
        """
        Busca uma transportadora padrão ativa
        """
        try:
            print(f"[TRANSPORTADORAS] Buscando transportadora padrão")
            
            criteria = {
                "expression": {
                    "$": "this.FORNECEDOR = ? AND this.ATIVO = ?"
                },
                "parameter": [
                    {"$": "S", "type": "S"},
                    {"$": "S", "type": "S"}
                ]
            }
            
            result = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,FORNECEDOR,ATIVO",
                criteria=criteria,
                limit=1
            )
            
            entities = result.get('responseBody', {}).get('entities', {})
            total = int(entities.get('total', '0'))
            
            if total > 0:
                entity = entities.get('entity')
                if isinstance(entity, list):
                    entity = entity[0]
                
                transportadora = {
                    'CODPARC': self._extract_value(entity.get('f0')),
                    'NOMEPARC': self._extract_value(entity.get('f1')),
                    'FORNECEDOR': self._extract_value(entity.get('f2')),
                    'ATIVO': self._extract_value(entity.get('f3'))
                }
                
                print(f"[TRANSPORTADORAS] Transportadora padrão: {transportadora['NOMEPARC']}")
                return transportadora
            
            print(f"[TRANSPORTADORAS] Nenhuma transportadora padrão encontrada")
            return None
            
        except Exception as e:
            print(f"[TRANSPORTADORAS] Erro ao buscar transportadora padrão: {e}")
            return None
    
    def listar_transportadoras_ativas(self, limite=10):
        """
        Lista transportadoras ativas (fornecedores)
        """
        try:
            criteria = {
                "expression": {
                    "$": "this.FORNECEDOR = ? AND this.ATIVO = ?"
                },
                "parameter": [
                    {"$": "S", "type": "S"},
                    {"$": "S", "type": "S"}
                ]
            }
            
            result = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,AD_IDALLPOST",
                criteria=criteria,
                limit=limite
            )
            
            entities = result.get('responseBody', {}).get('entities', {})
            total = int(entities.get('total', '0'))
            
            print(f"[TRANSPORTADORAS] Total transportadoras ativas: {total}")
            
            if total > 0:
                entity_list = entities.get('entity', [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                transportadoras = []
                for entity in entity_list:
                    transp = {
                        'CODPARC': self._extract_value(entity.get('f0')),
                        'NOMEPARC': self._extract_value(entity.get('f1')),
                        'AD_IDALLPOST': self._extract_value(entity.get('f2'))
                    }
                    transportadoras.append(transp)
                
                return entity_list  # Retorna formato original para compatibilidade
            
            return []
            
        except Exception as e:
            print(f"[TRANSPORTADORAS] Erro ao listar transportadoras: {e}")
            return []
    
    def validar_transportadora_ativa(self, codparc):
        """
        Valida se CODPARC é uma transportadora ativa
        """
        if not codparc:
            return False
            
        criteria = {
            "expression": {"$": "this.CODPARC = ? AND this.FORNECEDOR = ? AND this.ATIVO = ?"},
            "parameter": [
                {"type": "I", "value": str(codparc)},
                {"type": "S", "value": "S"},
                {"type": "S", "value": "S"}
            ]
        }
        
        try:
            result = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC",
                criteria=criteria
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            is_valid = total > 0
            
            if is_valid:
                entity = entities.get("entity")
                nome = self._extract_value(entity.get("f1")) if entity else "N/A"
                print(f"[TRANSPORTADORAS] CODPARC válido: {codparc} - {nome}")
            else:
                print(f"[TRANSPORTADORAS] CODPARC inválido ou não é transportadora ativa: {codparc}")
            
            return is_valid
            
        except Exception as e:
            print(f"[TRANSPORTADORAS] Erro na validação: {e}")
            return False
    
    def consultar_por_codparc(self, codparc):
        """
        Consulta transportadora por CODPARC
        """
        if not codparc:
            return None
            
        criteria = {
            "expression": {"$": "this.CODPARC = ?"},
            "parameter": [{
                "type": "I",
                "value": str(codparc)
            }]
        }
        
        try:
            result = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,AD_IDALLPOST,FORNECEDOR,ATIVO",
                criteria=criteria
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            if entities.get("total", "0") == "0":
                return None
                
            entity = entities.get("entity")
            if not entity:
                return None
                
            transportadora = {
                "CODPARC": self._extract_value(entity.get("f0")),
                "NOMEPARC": self._extract_value(entity.get("f1")),
                "AD_IDALLPOST": self._extract_value(entity.get("f2")),
                "FORNECEDOR": self._extract_value(entity.get("f3")),
                "ATIVO": self._extract_value(entity.get("f4"))
            }
            
            return transportadora
            
        except Exception as e:
            print(f"[TRANSPORTADORAS] Erro na consulta por CODPARC: {e}")
            return None
    
    # Métodos auxiliares para extrair dados específicos do WooCommerce
    def _extrair_prazo_entrega(self, meta_data):
        """Extrai prazo de entrega dos meta dados"""
        for meta in meta_data:
            if meta.get('key') == 'delivery_time':
                return meta.get('value', '')
        return ''
    
    def _extrair_metodo_transporte(self, meta_data):
        """Extrai método de transporte dos meta dados"""
        for meta in meta_data:
            if meta.get('key') == 'allpost_metodo':
                return meta.get('value', '')
        return ''