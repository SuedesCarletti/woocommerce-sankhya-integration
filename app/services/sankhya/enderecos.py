from .base import SankhyaClient
from utils.normalize import normalizar_nome

class EnderecosService(SankhyaClient):
    """
    Serviço para gestão de endereços e bairros no Sankhya
    VERSÃO CORRIGIDA: SEMPRE CONSULTA ANTES DE CRIAR
    """
    
    def consultar_endereco(self, nome_endereco):
        """
        Consulta endereço por nome
        """
        if not nome_endereco:
            return None
            
        criteria = {
            "expression": {"$": "UPPER(this.NOMEEND) = ?"},
            "parameter": [{
                "type": "S",
                "value": normalizar_nome(nome_endereco)
            }]
        }
        
        try:
            result = self.load_records(
                entity="Endereco",
                fields="CODEND,NOMEEND,TIPO,CODLOGRADOURO",
                criteria=criteria
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            if entities.get("total", "0") == "0":
                return None
                
            entity = entities.get("entity")
            if not entity:
                return None
                
            endereco = {
                "CODEND": entity["f0"]["$"],
                "NOMEEND": entity["f1"]["$"],
                "TIPO": entity["f2"]["$"],
                "CODLOGRADOURO": entity["f3"].get("$", "")
            }
            
            print(f"[ENDEREÇOS] Encontrado: {endereco['CODEND']} - {endereco['NOMEEND']}")
            return endereco
            
        except Exception as e:
            print(f"[ENDEREÇOS] Erro na consulta: {e}")
            return None
    
    def cadastrar_endereco(self, nome_endereco, tipo="RUA"):
        """
        Cadastra um novo endereço APENAS APÓS CONSULTAR
        """
        # NOVA VALIDAÇÃO: Sempre consulta antes de criar
        endereco_existente = self.consultar_endereco(nome_endereco)
        if endereco_existente:
            print(f"[ENDEREÇOS] Endereço já existe, reutilizando: {endereco_existente['CODEND']} - {endereco_existente['NOMEEND']}")
            return endereco_existente
        
        # Só cria se realmente não existir
        local_fields = {
            "NOMEEND": {"$": normalizar_nome(nome_endereco)},
            "TIPO": {"$": tipo.upper()}
        }
        
        fieldset = "CODEND,NOMEEND,TIPO,CODLOGRADOURO"
        
        try:
            print(f"[ENDEREÇOS] Criando novo endereço: {nome_endereco} ({tipo})")
            result = self.save_record("Endereco", local_fields, fieldset)
            
            entities = result.get("responseBody", {}).get("entities", {})
            entity = entities.get("entity", {})
            
            endereco = {
                "CODEND": entity.get("CODEND", {}).get("$", ""),
                "NOMEEND": entity.get("NOMEEND", {}).get("$", ""),
                "TIPO": entity.get("TIPO", {}).get("$", ""),
                "CODLOGRADOURO": entity.get("CODLOGRADOURO", {}).get("$", "")
            }
            
            print(f"[ENDEREÇOS] Cadastrado: {endereco['CODEND']} - {endereco['NOMEEND']}")
            return endereco
            
        except Exception as e:
            print(f"[ENDEREÇOS] Erro ao cadastrar: {e}")
            raise
    
    def obter_ou_criar_endereco(self, nome_endereco, tipo="RUA"):
        """
        Busca endereço existente ou cria novo
        AGORA TOTALMENTE SEGURO - cadastrar_endereco() já consulta internamente
        """
        if not nome_endereco:
            return None
            
        # Agora cadastrar_endereco() já faz a consulta internamente
        return self.cadastrar_endereco(nome_endereco, tipo)
    
    def consultar_bairro(self, nome_bairro):
        """
        Consulta bairro por nome
        """
        if not nome_bairro:
            return None
            
        criteria = {
            "expression": {"$": "UPPER(this.NOMEBAI) = ?"},
            "parameter": [{
                "type": "S",
                "value": normalizar_nome(nome_bairro)
            }]
        }
        
        try:
            result = self.load_records(
                entity="Bairro",
                fields="CODBAI,NOMEBAI",
                criteria=criteria
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            if entities.get("total", "0") == "0":
                return None
                
            entity = entities.get("entity")
            if not entity:
                return None
                
            bairro = {
                "CODBAI": entity["f0"]["$"],
                "NOMEBAI": entity["f1"]["$"]
            }
            
            print(f"[BAIRROS] Encontrado: {bairro['CODBAI']} - {bairro['NOMEBAI']}")
            return bairro
            
        except Exception as e:
            print(f"[BAIRROS] Erro na consulta: {e}")
            return None
    
    def cadastrar_bairro(self, nome_bairro):
        """
        Cadastra um novo bairro APENAS APÓS CONSULTAR
        """
        # NOVA VALIDAÇÃO: Sempre consulta antes de criar
        bairro_existente = self.consultar_bairro(nome_bairro)
        if bairro_existente:
            print(f"[BAIRROS] Bairro já existe, reutilizando: {bairro_existente['CODBAI']} - {bairro_existente['NOMEBAI']}")
            return bairro_existente
        
        # Só cria se realmente não existir
        local_fields = {
            "NOMEBAI": {"$": normalizar_nome(nome_bairro)}
        }
        
        fieldset = "CODBAI,NOMEBAI"
        
        try:
            print(f"[BAIRROS] Criando novo bairro: {nome_bairro}")
            result = self.save_record("Bairro", local_fields, fieldset)
            
            entities = result.get("responseBody", {}).get("entities", {})
            entity = entities.get("entity", {})
            
            bairro = {
                "CODBAI": entity.get("CODBAI", {}).get("$", ""),
                "NOMEBAI": entity.get("NOMEBAI", {}).get("$", "")
            }
            
            print(f"[BAIRROS] Cadastrado: {bairro['CODBAI']} - {bairro['NOMEBAI']}")
            return bairro
            
        except Exception as e:
            print(f"[BAIRROS] Erro ao cadastrar: {e}")
            raise
    
    def obter_ou_criar_bairro(self, nome_bairro):
        """
        Busca bairro existente ou cria novo
        AGORA TOTALMENTE SEGURO - cadastrar_bairro() já consulta internamente
        """
        if not nome_bairro:
            return None
            
        # Agora cadastrar_bairro() já faz a consulta internamente
        return self.cadastrar_bairro(nome_bairro)
    
    def processar_endereco_woocommerce(self, dados_endereco):
        """
        Processa dados de endereço do WooCommerce
        AGORA TOTALMENTE SEGURO contra duplicações
        """
        if not dados_endereco:
            return None, None
            
        endereco_nome = dados_endereco.get("address_1", "")
        bairro_nome = dados_endereco.get("neighborhood", "") or dados_endereco.get("city", "")
        
        codend = None
        codbai = None
        
        # Processa endereço (agora seguro contra duplicação)
        if endereco_nome:
            endereco = self.obter_ou_criar_endereco(endereco_nome, "RUA")
            if endereco:
                codend = endereco["CODEND"]
                print(f"[ENDEREÇOS] Processado: {endereco_nome} -> {codend}")
        
        # Processa bairro (agora seguro contra duplicação)
        if bairro_nome:
            bairro = self.obter_ou_criar_bairro(bairro_nome)
            if bairro:
                codbai = bairro["CODBAI"]
                print(f"[BAIRROS] Processado: {bairro_nome} -> {codbai}")
        
        return codend, codbai
    
    def listar_tipos_endereco_validos(self):
        """
        Lista tipos de endereço válidos no sistema
        """
        return ["RUA", "AVENIDA", "TRAVESSA", "ALAMEDA", "ESTRADA", "RODOVIA", "PRACA", "LARGO", "LADEIRA"]
    
    def normalizar_tipo_endereco(self, tipo_woocommerce):
        """
        Normaliza tipo de endereço do WooCommerce para Sankhya
        """
        if not tipo_woocommerce:
            return "RUA"  # Padrão
        
        tipo_upper = tipo_woocommerce.upper().strip()
        
        # Mapeamento de tipos comuns
        mapeamento = {
            "STREET": "RUA",
            "AVENUE": "AVENIDA", "AV": "AVENIDA", "AVE": "AVENIDA",
            "ROAD": "ESTRADA", "RD": "ESTRADA",
            "LANE": "TRAVESSA", "LN": "TRAVESSA",
            "BOULEVARD": "AVENIDA", "BLVD": "AVENIDA",
            "SQUARE": "PRACA", "SQ": "PRACA",
            "PLACE": "LARGO", "PL": "LARGO"
        }
        
        tipo_normalizado = mapeamento.get(tipo_upper, tipo_upper)
        
        # Verifica se é um tipo válido
        tipos_validos = self.listar_tipos_endereco_validos()
        if tipo_normalizado not in tipos_validos:
            print(f"[ENDEREÇOS] Tipo '{tipo_woocommerce}' não reconhecido, usando 'RUA'")
            return "RUA"
        
        return tipo_normalizado