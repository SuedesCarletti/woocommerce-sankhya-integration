from .base import SankhyaClient
from utils.normalize import normalizar_nome

class CidadesService(SankhyaClient):
    """
    Serviço para consulta de cidades no Sankhya (SOMENTE CONSULTA)
    VERSÃO CORRIGIDA: Seguindo documentação oficial de critérios
    """
    
    def consultar_por_nome_uf(self, nome_cidade, uf):
        """
        Seguindo documentação oficial de critérios
        """
        if not nome_cidade or not uf:
            return None
            
        # CORREÇÃO: Seguindo documentação "Utilizando Critérios em Consultas"
        criteria = {
            "expression": {
                "$": "UPPER(this.NOMECID) = ? AND UPPER(this.UF) = ?"
            },
            "parameter": [
                {
                    "$": normalizar_nome(nome_cidade),
                    "type": "S"
                },
                {
                    "$": uf.upper().strip(),
                    "type": "S"
                }
            ]
        }
        
        try:
            result = self.load_records(
                entity="Cidade",
                fields="CODCID,NOMECID,UF,CODREG",
                criteria=criteria
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total == 0:
                print(f"[CIDADES] Não encontrada: {nome_cidade}/{uf}")
                return None
                
            entity = entities.get("entity")
            if not entity:
                return None
                
            # Mapeia campos conforme metadata
            metadata = entities.get("metadata", {}).get("fields", {}).get("field", [])
            cidade = {}
            
            for i, field_info in enumerate(metadata):
                field_name = field_info.get("name")
                field_key = f"f{i}"
                if field_key in entity:
                    cidade[field_name] = entity[field_key].get("$", "")
            
            print(f"[CIDADES] Encontrada: {cidade.get('CODCID')} - {cidade.get('NOMECID')}/{cidade.get('UF')}")
            return cidade
            
        except Exception as e:
            print(f"[CIDADES] Erro na consulta: {e}")
            return None
    
    def consultar_qualquer_cidade_sp(self):
        """
        Busca qualquer cidade de SP como fallback
        """
        criteria = {
            "expression": {
                "$": "UPPER(this.UF) = ?"
            },
            "parameter": [
                {
                    "$": "SP",
                    "type": "S"
                }
            ]
        }
        
        try:
            result = self.load_records(
                entity="Cidade",
                fields="CODCID,NOMECID,UF,CODREG",
                criteria=criteria
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity = entities.get("entity")
                if isinstance(entity, list):
                    entity = entity[0]
                
                # Mapeia campos conforme metadata
                metadata = entities.get("metadata", {}).get("fields", {}).get("field", [])
                cidade = {}
                
                for i, field_info in enumerate(metadata):
                    field_name = field_info.get("name")
                    field_key = f"f{i}"
                    if field_key in entity:
                        cidade[field_name] = entity[field_key].get("$", "")
                
                print(f"[CIDADES] Primeira cidade SP disponível: {cidade.get('NOMECID')}/{cidade.get('UF')}")
                return cidade
            
            return None
            
        except Exception as e:
            print(f"[CIDADES] Erro ao buscar cidade SP: {e}")
            return None
    
    def buscar_primeira_cidade_disponivel(self):
        """
        Busca primeira cidade disponível sem critérios
        """
        try:
            result = self.load_records(
                entity="Cidade",
                fields="CODCID,NOMECID,UF,CODREG",
                criteria=None
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity = entities.get("entity")
                if isinstance(entity, list):
                    entity = entity[0]
                elif not entity:
                    return None
                
                # Mapeia campos conforme metadata
                metadata = entities.get("metadata", {}).get("fields", {}).get("field", [])
                cidade = {}
                
                for i, field_info in enumerate(metadata):
                    field_name = field_info.get("name")
                    field_key = f"f{i}"
                    if field_key in entity:
                        cidade[field_name] = entity[field_key].get("$", "")
                
                print(f"[CIDADES] Primeira cidade disponível: {cidade.get('NOMECID')}/{cidade.get('UF')}")
                return cidade
            
            return None
            
        except Exception as e:
            print(f"[CIDADES] Erro ao buscar primeira cidade: {e}")
            return None
    
    def obter_cidade_padrao_robusta(self):
        """
        Tentativas múltiplas para encontrar cidade padrão
        """
        print(f"[CIDADES] Buscando cidade padrão com múltiplas tentativas...")
        
        # Tentativa 1: São Paulo exato
        cidade = self.consultar_por_nome_uf("SAO PAULO", "SP")
        if cidade:
            return cidade
        
        # Tentativa 2: Variações de São Paulo
        variacoes_sp = ["SÃO PAULO", "Sao Paulo", "São Paulo", "SAOPAULO"]
        for variacao in variacoes_sp:
            cidade = self.consultar_por_nome_uf(variacao, "SP")
            if cidade:
                print(f"[CIDADES] Encontrada variação: {variacao}")
                return cidade
        
        # Tentativa 3: Qualquer cidade de SP
        cidade = self.consultar_qualquer_cidade_sp()
        if cidade:
            return cidade
        
        # Tentativa 4: Primeira cidade disponível do sistema
        cidade = self.buscar_primeira_cidade_disponivel()
        if cidade:
            print(f"[CIDADES] Usando primeira cidade disponível: {cidade.get('NOMECID')}/{cidade.get('UF')}")
            return cidade
        
        print(f"[CIDADES] ERRO CRÍTICO: Nenhuma cidade encontrada no sistema!")
        return None
    
    def consultar_por_nome_parcial(self, nome_cidade, uf=None):
        """
        Consulta cidade com busca parcial (LIKE)
        """
        if not nome_cidade:
            return None
            
        nome_normalizado = normalizar_nome(nome_cidade)
        
        if uf:
            expression = "UPPER(this.NOMECID) LIKE ? AND UPPER(this.UF) = ?"
            parameters = [
                {
                    "$": f"%{nome_normalizado}%",
                    "type": "S"
                },
                {
                    "$": uf.upper().strip(),
                    "type": "S"
                }
            ]
        else:
            expression = "UPPER(this.NOMECID) LIKE ?"
            parameters = [
                {
                    "$": f"%{nome_normalizado}%",
                    "type": "S"
                }
            ]
        
        criteria = {
            "expression": {"$": expression},
            "parameter": parameters
        }
        
        try:
            result = self.load_records(
                entity="Cidade",
                fields="CODCID,NOMECID,UF,CODREG",
                criteria=criteria
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total == 0:
                return None
            
            entity = entities.get("entity")
            if isinstance(entity, list):
                entity = entity[0]
                
            # Mapeia campos conforme metadata
            metadata = entities.get("metadata", {}).get("fields", {}).get("field", [])
            cidade = {}
            
            for i, field_info in enumerate(metadata):
                field_name = field_info.get("name")
                field_key = f"f{i}"
                if field_key in entity:
                    cidade[field_name] = entity[field_key].get("$", "")
            
            print(f"[CIDADES] Encontrada (parcial): {cidade.get('CODCID')} - {cidade.get('NOMECID')}/{cidade.get('UF')}")
            return cidade
            
        except Exception as e:
            print(f"[CIDADES] Erro na consulta parcial: {e}")
            return None
    
    def consultar_capital_estado(self, uf):
        """
        Consulta capital do estado como fallback
        """
        capitais = {
            "AC": "RIO BRANCO", "AL": "MACEIO", "AP": "MACAPA", "AM": "MANAUS",
            "BA": "SALVADOR", "CE": "FORTALEZA", "DF": "BRASILIA", "ES": "VITORIA",
            "GO": "GOIANIA", "MA": "SAO LUIS", "MT": "CUIABA", "MS": "CAMPO GRANDE",
            "MG": "BELO HORIZONTE", "PA": "BELEM", "PB": "JOAO PESSOA", "PR": "CURITIBA",
            "PE": "RECIFE", "PI": "TERESINA", "RJ": "RIO DE JANEIRO", "RN": "NATAL",
            "RS": "PORTO ALEGRE", "RO": "PORTO VELHO", "RR": "BOA VISTA", 
            "SC": "FLORIANOPOLIS", "SP": "SAO PAULO", "SE": "ARACAJU", "TO": "PALMAS"
        }
        
        capital = capitais.get(uf.upper())
        if capital:
            print(f"[CIDADES] Tentando capital {capital}/{uf}")
            return self.consultar_por_nome_uf(capital, uf)
        
        return None
    
    def processar_endereco_woocommerce(self, dados_endereco):
        """
        Processa endereço do WooCommerce e sempre retorna uma cidade
        """
        if not dados_endereco:
            print(f"[CIDADES] Sem dados de endereço, buscando cidade padrão...")
            return self.obter_cidade_padrao_robusta()
        
        cidade_nome = dados_endereco.get("city", "").strip()
        estado = dados_endereco.get("state", "").strip()
        
        print(f"[CIDADES] Processando: cidade='{cidade_nome}', estado='{estado}'")
        
        # Mapeia estados do WooCommerce para UF
        uf_normalizada = self._normalizar_estado(estado)
        
        if not cidade_nome:
            print(f"[CIDADES] Nome da cidade vazio")
            if uf_normalizada:
                cidade = self.consultar_capital_estado(uf_normalizada)
                if cidade:
                    return cidade
            return self.obter_cidade_padrao_robusta()
        
        # 1. Tentativa: busca exata
        if uf_normalizada:
            cidade = self.consultar_por_nome_uf(cidade_nome, uf_normalizada)
            if cidade:
                return cidade
        
        # 2. Tentativa: busca parcial com UF
        if uf_normalizada:
            cidade = self.consultar_por_nome_parcial(cidade_nome, uf_normalizada)
            if cidade:
                return cidade
        
        # 3. Tentativa: busca parcial sem UF
        cidade = self.consultar_por_nome_parcial(cidade_nome)
        if cidade:
            return cidade
        
        # 4. Tentativa: capital do estado
        if uf_normalizada:
            cidade = self.consultar_capital_estado(uf_normalizada)
            if cidade:
                print(f"[CIDADES] Cidade '{cidade_nome}' não encontrada, usando capital {cidade['NOMECID']}")
                return cidade
        
        # 5. Fallback: Cidade padrão robusta
        cidade_padrao = self.obter_cidade_padrao_robusta()
        if cidade_padrao:
            print(f"[CIDADES] Usando cidade padrão: {cidade_padrao['NOMECID']}/{cidade_padrao['UF']}")
            return cidade_padrao
        
        # 6. Se chegou aqui, é um erro crítico
        raise ValueError("ERRO CRÍTICO: Nenhuma cidade encontrada no Sankhya - verifique se há cidades cadastradas no sistema")
    
    def _normalizar_estado(self, estado):
        """
        Normaliza estado do WooCommerce para UF padrão
        """
        if not estado:
            return None
        
        estado_upper = estado.upper().strip()
        
        if len(estado_upper) == 2:
            return estado_upper
        
        mapa_estados = {
            "ACRE": "AC", "ALAGOAS": "AL", "AMAPA": "AP", "AMAPÁ": "AP",
            "AMAZONAS": "AM", "BAHIA": "BA", "CEARA": "CE", "CEARÁ": "CE",
            "DISTRITO FEDERAL": "DF", "ESPIRITO SANTO": "ES", "ESPÍRITO SANTO": "ES",
            "GOIAS": "GO", "GOIÁS": "GO", "MARANHAO": "MA", "MARANHÃO": "MA",
            "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS", "MINAS GERAIS": "MG",
            "PARA": "PA", "PARÁ": "PA", "PARAIBA": "PB", "PARAÍBA": "PB",
            "PARANA": "PR", "PARANÁ": "PR", "PERNAMBUCO": "PE", "PIAUI": "PI", "PIAUÍ": "PI",
            "RIO DE JANEIRO": "RJ", "RIO GRANDE DO NORTE": "RN", "RIO GRANDE DO SUL": "RS",
            "RONDONIA": "RO", "RONDÔNIA": "RO", "RORAIMA": "RR", "SANTA CATARINA": "SC",
            "SAO PAULO": "SP", "SÃO PAULO": "SP", "SERGIPE": "SE", "TOCANTINS": "TO"
        }
        
        uf = mapa_estados.get(estado_upper)
        if uf:
            print(f"[CIDADES] Estado '{estado}' normalizado para: {uf}")
            return uf
        
        print(f"[CIDADES] Estado '{estado}' não reconhecido")
        return None
    
    def listar_cidades_sistema(self, limite=10):
        """
        Lista cidades disponíveis no sistema para debug
        """
        try:
            result = self.load_records(
                entity="Cidade",
                fields="CODCID,NOMECID,UF,CODREG",
                criteria=None
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            print(f"[CIDADES] Sistema tem {total} cidades cadastradas")
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                metadata = entities.get("metadata", {}).get("fields", {}).get("field", [])
                
                print(f"[CIDADES] Primeiras {min(limite, len(entity_list))} cidades:")
                for i, entity in enumerate(entity_list[:limite]):
                    # Mapeia usando metadata
                    cidade_info = {}
                    for j, field_info in enumerate(metadata):
                        field_name = field_info.get("name")
                        field_key = f"f{j}"
                        if field_key in entity:
                            cidade_info[field_name] = entity[field_key].get("$", "")
                    
                    cidade_nome = cidade_info.get("NOMECID", "N/A")
                    cidade_uf = cidade_info.get("UF", "N/A")
                    print(f"[CIDADES]   {i+1}. {cidade_nome}/{cidade_uf}")
            
            return total > 0
            
        except Exception as e:
            print(f"[CIDADES] Erro ao listar cidades: {e}")
            return False