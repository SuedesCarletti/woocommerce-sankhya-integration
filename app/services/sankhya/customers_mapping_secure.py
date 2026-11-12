"""
CustomerMappingService CORRIGIDO - Versão Integrada com Arquitetura do Projeto
Versão: 3.2.0 - Adicionado fallback de bairro para cidade.
CORRIGIDO: Busca por endereço/bairro, tratamento de resposta em lista e fluxo de mapeamento.
"""

import re
from typing import Dict, List
import requests
from .base import SankhyaClient

class CustomerMappingService(SankhyaClient):
    """
    ✅ CORRIGIDO: Herda de SankhyaClient e integra com arquitetura existente
    """
    
    def __init__(self, token=None, parceiros_service=None):
        super().__init__(token)
        self.parceiros_service = parceiros_service
        self.cache = {
            'ufs': {},
            'cidades_ibge': {},
            'enderecos_keywords': {},
            'bairros_keywords': {}
        }
        self.stats = {
            'consultas_db': 0,
            'cache_hits': 0,
            'criados_endereco': 0,
            'criados_bairro': 0,
            'validacoes': 0,
            'rejeicoes': 0
        }

    def realizar_mapeamento_completo(self, dados_cliente: Dict) -> Dict:
        """
        Mapeia todos os dados necessários para cadastro
        """
        billing = dados_cliente.get('billing', {})
        
        resultado = {
            'todos_mapeados': False,
            'codreg': None,
            'codcid': None, 
            'codend': None,
            'codbai': None,
            'detalhes': {}
        }
        
        print(f"[CUSTOMER MAPPING] Iniciando mapeamento completo...")
        
        # 1. UF - MAPEAMENTO PADRÃO
        uf_result = self._mapear_uf_padrao(billing.get('state', ''))
        resultado['codreg'] = uf_result.get('codreg')
        resultado['detalhes']['uf'] = uf_result
        
        # 2. CIDADE - MAPEAMENTO VIA IBGE
        ibge_code = self._obter_codigo_ibge_dos_metadados(dados_cliente)
        cidade_result = self._mapear_cidade_via_ibge(ibge_code or '')
        resultado['codcid'] = cidade_result.get('codcid')
        resultado['detalhes']['cidade'] = cidade_result
        
        # 3. ENDEREÇO - BUSCA INTELIGENTE
        endereco_result = self._mapear_endereco_3_palavras(billing.get('address_1', ''))
        resultado['codend'] = endereco_result.get('codend')
        resultado['detalhes']['endereco'] = endereco_result
        
        # MELHORIA: Lógica de fallback para o bairro.
        # Se o bairro não for informado, usa o nome da cidade como fallback.
        nome_bairro_para_busca = billing.get('neighborhood', '')
        if not nome_bairro_para_busca:
            nome_cidade = billing.get('city', '')
            if nome_cidade:
                print(f"[CUSTOMER MAPPING] ℹBairro não informado. Usando o nome da cidade como fallback: '{nome_cidade}'")
                nome_bairro_para_busca = nome_cidade
        
        # 4. BAIRRO - BUSCA INTELIGENTE COM FALLBACK
        bairro_result = self._mapear_bairro_3_palavras(nome_bairro_para_busca)
        resultado['codbai'] = bairro_result.get('codbai')
        resultado['detalhes']['bairro'] = bairro_result
        
        # VERIFICAÇÃO FINAL
        resultado['todos_mapeados'] = all([
            resultado['codreg'],
            resultado['codcid'],
            resultado['codend'],
            resultado['codbai']
        ])
        
        if resultado['todos_mapeados']:
            print(f"[CUSTOMER MAPPING] Mapeamento completo realizado com sucesso!")
        else:
            # Log aprimorado para dizer exatamente o que faltou
            partes_faltando = []
            if not resultado['codreg']: partes_faltando.append('codreg')
            if not resultado['codcid']: partes_faltando.append('codcid')
            if not resultado['codend']: partes_faltando.append('codend')
            if not resultado['codbai']: partes_faltando.append('codbai')
            print(f"[CUSTOMER MAPPING] Mapeamento incompleto - verifique detalhes. Faltando: {', '.join(partes_faltando)}")
        
        return resultado

    def cadastrar_cliente_completo(self, dados_cliente: Dict) -> Dict:
        """
        Realiza mapeamento + cadastro usando parceiros_service
        """
        try:
            mapeamento = self.realizar_mapeamento_completo(dados_cliente)
            
            if not mapeamento['todos_mapeados']:
                return {
                    'sucesso': False,
                    'erro': 'Mapeamento incompleto - impossível cadastrar',
                    'detalhes': mapeamento['detalhes']
                }
            
            return self._cadastrar_no_sankhya(dados_cliente, mapeamento)
            
        except Exception as e:
            return {'sucesso': False, 'erro': f'Erro no processo completo: {str(e)}'}

    def _extrair_3_palavras_principais(self, texto: str) -> List[str]:
            """
            💡 MELHORIA: Extrai até 3 palavras mais significativas, ignorando stop words.
            ✅ CORREÇÃO: "Jardim" foi removido das stop words para nomes de bairro.
            """
            if not texto:
                return []
            
            texto_limpo = re.sub(r'[^\w\s]', '', texto.upper())
            palavras = texto_limpo.split()
            
            # CORREÇÃO: Lista de stop words de logradouros, não de bairros.
            stop_words = {
                'DE', 'DA', 'DO', 'DOS', 'DAS', 'E', 'A', 'O', 'EM', 'NA', 'NO', 'COM',
                'RUA', 'AV', 'AVENIDA', 'AL', 'ALAMEDA', 'TRAVESSA', 'TRV', 'ESTRADA',
                'PRAÇA', 'PRACA', 'PÇA', 'PC', 'LARGO', 'RODOVIA'
                # As palavras 'JD' e 'JARDIM' foram removidas daqui.
            }
            palavras_filtradas = [p for p in palavras if len(p) >= 3 and p not in stop_words]
            
            if not palavras_filtradas and palavras:
                return palavras[:3]
            
            return palavras_filtradas[:3]
    
    def _mapear_endereco_3_palavras(self, endereco: str) -> Dict:
        """
        ✅ FOCO: Buscar CODEND existente no Sankhya para reutilizar com lógica aprimorada.
        """
        if not endereco:
            return {'sucesso': False, 'erro': 'Endereço não informado'}
        
        print(f"[CUSTOMER MAPPING] Buscando endereço existente: {endereco}")
        
        palavras = self._extrair_3_palavras_principais(endereco)
        if not palavras:
            return {'sucesso': False, 'erro': 'Não foi possível extrair palavras-chave do endereço'}

        # Tenta buscar o endereço com base nas palavras-chave
        resultado_busca = self._buscar_endereco_por_palavras(palavras)
        if resultado_busca.get('sucesso'):
            codend = resultado_busca['codend']
            print(f"[CUSTOMER MAPPING] Endereço encontrado via busca: CODEND={codend}")
            self._log_mapeamento('endereco', endereco, codend, 'reutilizado')
            return resultado_busca

        # Se não encontrar, tenta criar (último recurso)
        print(f"[CUSTOMER MAPPING] Endereço não encontrado na busca, tentando criar...")
        resultado_criacao = self._criar_endereco_novo(endereco, palavras)
        if resultado_criacao.get('sucesso'):
            self._log_mapeamento('endereco', endereco, resultado_criacao['codend'], 'criado_novo')
        return resultado_criacao

    def _buscar_endereco_por_palavras(self, palavras: List[str]) -> Dict:
        """
        ✅ BUSCA MELHORADA: Tenta encontrar endereços com base em palavras significativas.
        """
        if not palavras:
            return {'sucesso': False, 'erro': 'Nenhuma palavra fornecida'}

        # Monta a expressão de busca com todas as palavras-chave
        like_clauses = " AND ".join([f"UPPER(this.NOMEEND) LIKE ?" for _ in palavras])
        parameters = [{"$": f"%{p.upper()}%", "type": "S"} for p in palavras]
        
        criteria = {
            "expression": {"$": like_clauses},
            "parameter": parameters
        }
        
        print(f"[CUSTOMER MAPPING] Buscando endereço com: {palavras}")
        
        try:
            result = self.load_records(entity="Endereco", fields="CODEND,NOMEEND,TIPO", criteria=criteria, limit=5)
            
            entities = result.get("responseBody", {}).get("entities", {})
            if int(entities.get("total", "0")) > 0:
                # CORREÇÃO: Trata a resposta sempre como uma lista para evitar o erro.
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list] # Garante que seja sempre uma lista

                # Pega o primeiro resultado da lista
                primeiro_endereco = entity_list[0]
                codend = self._extract_value(primeiro_endereco.get('f0'))
                nomeend = self._extract_value(primeiro_endereco.get('f1'))
                
                if codend:
                    print(f"[CUSTOMER MAPPING] Endereço correspondente encontrado: CODEND={codend} - {nomeend}")
                    return {'sucesso': True, 'codend': int(codend), 'fonte': 'encontrado'}
            
        except Exception as e:
            print(f"[CUSTOMER MAPPING] Erro na busca de endereço: {str(e)}")
        
        return {'sucesso': False, 'erro': 'Endereço não encontrado com as palavras-chave'}


    def _criar_endereco_novo(self, endereco: str, palavras_chave: List[str]) -> Dict:
        """
        ✅ ÚLTIMO RECURSO: Só cria se realmente não existir (com validação de duplicata)
        """
        try:
            nome_logradouro = self._extrair_nome_logradouro(endereco)
            tipo_logradouro = self._determinar_tipo_logradouro(endereco)
            
            print(f"[CUSTOMER MAPPING] Tentando criar: {nome_logradouro} ({tipo_logradouro})")
            
            # ÚLTIMA VERIFICAÇÃO: Busca exata antes de criar
            criteria_exata = {
                "expression": {"$": "UPPER(this.NOMEEND) = ? AND UPPER(this.TIPO) = ?"},
                "parameter": [
                    {"$": nome_logradouro.upper(), "type": "S"},
                    {"$": tipo_logradouro.upper(), "type": "S"}
                ]
            }
            
            result_verificacao = self.load_records(entity="Endereco", fields="CODEND", criteria=criteria_exata, limit=1)
            entities_verificacao = result_verificacao.get("responseBody", {}).get("entities", {})

            if int(entities_verificacao.get("total", "0")) > 0:
                entity_list = entities_verificacao.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                codend_existente = self._extract_value(entity_list[0].get('f0'))
                if codend_existente:
                    print(f"[CUSTOMER MAPPING] Endereço já existe (encontrado na verificação final): CODEND={codend_existente}")
                    return {'sucesso': True, 'codend': int(codend_existente), 'fonte': 'encontrado_exato'}

            # Se chegou aqui, realmente não existe - cria novo
            payload = {
                "serviceName": "CRUDServiceProvider.saveRecord",
                "requestBody": {
                    "dataSet": {
                        "rootEntity": "Endereco", "includePresentationFields": "S",
                        "dataRow": {"localFields": {"NOMEEND": {"$": nome_logradouro[:60]}, "TIPO": {"$": tipo_logradouro}}},
                        "entity": {"fieldset": {"list": "CODEND,NOMEEND,TIPO"}}
                    }
                }
            }
            
            url = self.get_url("CRUDServiceProvider.saveRecord")
            result = self.post_request(url, payload)
            
            if result.get("status") == "1":
                codend = result.get("responseBody", {}).get("entities", {}).get("entity", {}).get("CODEND", {}).get("$")
                if codend:
                    self.stats['criados_endereco'] += 1
                    print(f"[CUSTOMER MAPPING] Novo endereço criado: CODEND={codend}")
                    return {'sucesso': True, 'codend': int(codend), 'fonte': 'criado_novo'}
                else:
                    return {'sucesso': False, 'erro': 'CODEND não retornado na resposta'}
            else:
                erro = result.get("statusMessage", "Erro desconhecido")
                if "Já existe" in erro:
                    print(f"[CUSTOMER MAPPING] Erro de duplicata. Tentando encontrar o endereço que já existe...")
                    return self._buscar_endereco_por_palavras(palavras_chave)
                return {'sucesso': False, 'erro': erro}
            
        except Exception as e:
            return {'sucesso': False, 'erro': f'Exceção ao criar endereço: {str(e)}'}

    def _mapear_bairro_3_palavras(self, bairro: str) -> Dict:
        """
        ✅ FOCO: Buscar CODBAI existente no Sankhya para reutilizar com lógica aprimorada.
        """
        if not bairro:
            return {'sucesso': False, 'erro': 'Bairro não informado'}
        
        print(f"[CUSTOMER MAPPING] Buscando bairro existente: {bairro}")
        
        palavras = self._extrair_3_palavras_principais(bairro)
        if not palavras:
            # Se o bairro original tem texto mas as palavras filtradas não, usa o bairro original
            palavras = bairro.split()[:3]
            print(f"[CUSTOMER MAPPING] ℹNenhuma palavra-chave extraída, usando palavras originais: {palavras}")


        resultado_busca = self._buscar_bairro_por_palavras(palavras)
        if resultado_busca.get('sucesso'):
            codbai = resultado_busca['codbai']
            print(f"[CUSTOMER MAPPING] Bairro encontrado via busca: CODBAI={codbai}")
            self._log_mapeamento('bairro', bairro, codbai, 'reutilizado')
            return resultado_busca
        
        print(f"[CUSTOMER MAPPING] Bairro não encontrado na busca, tentando criar...")
        resultado_criacao = self._criar_bairro_novo(bairro)
        if resultado_criacao.get('sucesso'):
            self._log_mapeamento('bairro', bairro, resultado_criacao['codbai'], 'criado_novo')
        return resultado_criacao

    def _buscar_bairro_por_palavras(self, palavras: List[str]) -> Dict:
        """
        ✅ BUSCA MELHORADA: Tenta encontrar bairros com base em palavras significativas.
        """
        if not palavras:
            return {'sucesso': False, 'erro': 'Nenhuma palavra fornecida'}

        like_clauses = " AND ".join([f"UPPER(this.NOMEBAI) LIKE ?" for _ in palavras])
        parameters = [{"$": f"%{p.upper()}%", "type": "S"} for p in palavras]
        
        criteria = {
            "expression": {"$": like_clauses},
            "parameter": parameters
        }

        print(f"[CUSTOMER MAPPING] Buscando bairro com: {palavras}")
        
        try:
            result = self.load_records(entity="Bairro", fields="CODBAI,NOMEBAI", criteria=criteria, limit=5)
            
            entities = result.get("responseBody", {}).get("entities", {})
            if int(entities.get("total", "0")) > 0:
                # CORREÇÃO: Trata a resposta sempre como uma lista.
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]

                primeiro_bairro = entity_list[0]
                codbai = self._extract_value(primeiro_bairro.get('f0'))
                nomebai = self._extract_value(primeiro_bairro.get('f1'))

                if codbai:
                    print(f"[CUSTOMER MAPPING] Bairro correspondente encontrado: CODBAI={codbai} - {nomebai}")
                    return {'sucesso': True, 'codbai': int(codbai), 'fonte': 'encontrado'}

        except Exception as e:
            print(f"[CUSTOMER MAPPING] Erro na busca de bairro: {str(e)}")
        
        return {'sucesso': False, 'erro': 'Bairro não encontrado com as palavras-chave'}

    def _criar_bairro_novo(self, bairro: str) -> Dict:
        """
        ✅ ÚLTIMO RECURSO: Só cria se realmente não existir.
        """
        try:
            nome_bairro = bairro.strip().upper()
            nome_bairro = re.sub(r'[^\w\s]', ' ', nome_bairro).strip()
            nome_bairro = re.sub(r'\s+', ' ', nome_bairro)

            if not nome_bairro:
                return {'sucesso': False, 'erro': 'Nome do bairro inválido após limpeza'}

            print(f"[CUSTOMER MAPPING] Tentando criar bairro: {nome_bairro}")
            
            # Verificação final
            criteria_exata = {"expression": {"$": "UPPER(this.NOMEBAI) = ?"}, "parameter": [{"$": nome_bairro, "type": "S"}]}
            result_verificacao = self.load_records(entity="Bairro", fields="CODBAI", criteria=criteria_exata, limit=1)
            entities_verificacao = result_verificacao.get("responseBody", {}).get("entities", {})

            if int(entities_verificacao.get("total", "0")) > 0:
                entity_list = entities_verificacao.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                codbai_existente = self._extract_value(entity_list[0].get('f0'))
                if codbai_existente:
                    print(f"[CUSTOMER MAPPING] Bairro já existe: CODBAI={codbai_existente}")
                    return {'sucesso': True, 'codbai': int(codbai_existente), 'fonte': 'encontrado_exato'}

            # Cria novo
            payload = {
                "serviceName": "CRUDServiceProvider.saveRecord",
                "requestBody": {
                    "dataSet": {
                        "rootEntity": "Bairro", "includePresentationFields": "S",
                        "dataRow": {"localFields": {"NOMEBAI": {"$": nome_bairro[:60]}}},
                        "entity": {"fieldset": {"list": "CODBAI,NOMEBAI"}}
                    }
                }
            }
            url = self.get_url("CRUDServiceProvider.saveRecord")
            result = self.post_request(url, payload)

            if result.get("status") == "1":
                codbai = result.get("responseBody",{}).get("entities",{}).get("entity",{}).get("CODBAI",{}).get("$")
                if codbai:
                    self.stats['criados_bairro'] += 1
                    print(f"[CUSTOMER MAPPING] Novo bairro criado: CODBAI={codbai}")
                    return {'sucesso': True, 'codbai': int(codbai), 'fonte': 'criado_novo'}
                return {'sucesso': False, 'erro': 'CODBAI não retornado'}
            else:
                erro = result.get("statusMessage", "Erro desconhecido")
                if "já existe" in erro.lower():
                     return self._buscar_bairro_por_palavras([nome_bairro])
                return {'sucesso': False, 'erro': erro}

        except Exception as e:
            return {'sucesso': False, 'erro': f'Exceção ao criar bairro: {str(e)}'}

    def _mapear_cidade_via_ibge(self, ibge_code: str) -> Dict:
        """
        Usa CODMUNFIS para buscar cidade.
        """
        if not ibge_code or len(str(ibge_code)) != 7:
            return {'sucesso': False, 'erro': 'Código IBGE inválido ou não fornecido'}
        
        criteria = {
            "expression": {"$": "this.CODMUNFIS = ?"},
            "parameter": [{"$": str(ibge_code), "type": "S"}]
        }
        
        try:
            result = self.load_records(entity="Cidade", fields="CODCID,NOMECID", criteria=criteria, limit=1)
            entities = result.get("responseBody", {}).get("entities", {})
            if int(entities.get("total", "0")) > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                codcid = self._extract_value(entity_list[0].get('f0'))
                if codcid:
                    print(f"[CUSTOMER MAPPING] Cidade encontrada por IBGE {ibge_code}: CODCID={codcid}")
                    return {'sucesso': True, 'codcid': int(codcid)}
            
            return {'sucesso': False, 'erro': f'Cidade não encontrada para IBGE {ibge_code}'}
            
        except Exception as e:
            return {'sucesso': False, 'erro': f'Erro na consulta de cidade: {str(e)}'}
    
    def _extract_value(self, field_obj):
        if not field_obj: return ""
        if isinstance(field_obj, dict): return field_obj.get('$', '')
        return str(field_obj) if field_obj is not None else ""

    def _cadastrar_no_sankhya(self, dados_cliente: Dict, mapeamento: Dict) -> Dict:
        try:
            if not self.parceiros_service:
                return {'sucesso': False, 'erro': 'Serviço de parceiros não disponível'}
            
            billing = dados_cliente.get('billing', {})
            nome_completo = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
            documento = self._extrair_documento_real(billing, dados_cliente)
            
            if not documento:
                return {'sucesso': False, 'erro': 'Documento (CPF/CNPJ) não encontrado para cadastro.'}

            print(f"[CUSTOMER MAPPING] Chamando parceiros.incluir() para '{nome_completo}'...")
            
            # Delega a criação para o ParceirosService, passando todos os IDs mapeados
            resultado = self.parceiros_service.incluir(
                nome=nome_completo,
                documento=documento,
                email=dados_cliente.get('email'),
                telefone=billing.get('phone'),
                endereco_completo=billing,
                # KWARGS ADICIONAIS que o `incluir` vai usar
                CODREG=mapeamento['codreg'],
                CODCID=mapeamento['codcid'],
                CODEND=mapeamento['codend'],
                CODBAI=mapeamento['codbai'],
                CLIENTE='S',
                ATIVO='S',
                TIPPESSOA='F' if len(documento) == 11 else 'J',
                CLASSIFICMS='C',
                CEP=re.sub(r'\D', '', billing.get('postcode', ''))[:8]
            )
            
            return resultado
            
        except Exception as e:
            return {'sucesso': False, 'erro': f'Erro no processo de cadastro: {str(e)}'}

    def _extrair_nome_logradouro(self, endereco: str) -> str:
        endereco_upper = endereco.upper().strip()
        prefixos = ['RUA ', 'AVENIDA ', 'AV ', 'ALAMEDA ', 'TRAVESSA ', 'ESTRADA ', 'PRAÇA ', 'LARGO ', 'RODOVIA ']
        nome_limpo = endereco_upper
        for prefixo in prefixos:
            if endereco_upper.startswith(prefixo):
                nome_limpo = endereco_upper[len(prefixo):].strip()
                break
        nome_limpo = re.sub(r'[^\w\s]', ' ', nome_limpo)
        nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip()
        return nome_limpo or endereco_upper

    def _determinar_tipo_logradouro(self, endereco: str) -> str:
        endereco_upper = endereco.upper()
        if 'AVENIDA' in endereco_upper or 'AV.' in endereco_upper or 'AV ' in endereco_upper: return 'AVENIDA'
        if 'ALAMEDA' in endereco_upper or 'AL.' in endereco_upper: return 'ALAMEDA'
        # ... outras regras
        return 'RUA'

    def _log_mapeamento(self, tipo: str, nome: str, codigo: int, fonte: str):
        emoji = "♻️" if 'reutilizado' in fonte else "🆕"
        print(f"[MAPPING] {emoji} {tipo.upper()} '{nome}' → ID={codigo} ({fonte})")

    def _extrair_documento_real(self, billing: Dict, dados_cliente: Dict) -> str:
        campos = ['cpf', 'cnpj', 'document', 'tax_id']
        for campo in campos:
            doc = billing.get(campo, '').strip() or dados_cliente.get(campo, '').strip()
            if doc: return re.sub(r'\D', '', doc)
        meta_data = dados_cliente.get('meta_data', [])
        for item in meta_data:
            if item.get('key') in ['billing_cpf', 'billing_cnpj']:
                doc = item.get('value', '').strip()
                if doc: return re.sub(r'\D', '', doc)
        return ''

    def _obter_codigo_ibge_dos_metadados(self, dados_cliente: Dict) -> str:
        meta_data = dados_cliente.get('meta_data', [])
        for item in meta_data:
            if item.get('key') == 'billing_ibge_code':
                ibge_code = item.get('value')
                if ibge_code and len(str(ibge_code)) == 7:
                    return ibge_code
        cep = dados_cliente.get('billing', {}).get('postcode', '')
        return self._buscar_ibge_via_cep(cep) if cep else None

    def _buscar_ibge_via_cep(self, cep: str) -> str:
        cep_limpo = re.sub(r'\D', '', cep)
        if len(cep_limpo) != 8: return None
        try:
            response = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=5)
            if response.status_code == 200 and not response.json().get('erro'):
                return response.json().get('ibge')
        except Exception as e:
            print(f"[CUSTOMER MAPPING] Erro ao buscar IBGE via CEP: {e}")
        return None

    def _mapear_uf_padrao(self, uf: str) -> Dict:
        if not uf: return {'sucesso': False, 'erro': 'UF não informada'}
        # Simulação de mapeamento, use sua lógica real aqui
        codigos_uf = {
            'AC': 100100, 'AL': 200100, 'AP': 300100, 'AM': 400100,
            'BA': 500100, 'CE': 600100, 'DF': 700100, 'ES': 800100,
            'GO': 900100, 'MA': 1000100, 'MT': 1100100, 'MS': 1200100,
            'MG': 1300100, 'PA': 1400100, 'PB': 1500100, 'PR': 1600100,
            'PE': 1700100, 'PI': 1800100, 'RJ': 1900100, 'RN': 2000100,
            'RS': 2100100, 'RO': 2200100, 'RR': 2300100, 'SC': 2400100,
            'SP': 2500100, 'SE': 2600100, 'TO': 2700100
        }
        codreg = codigos_uf.get(uf.upper())
        if codreg:
            return {'sucesso': True, 'codreg': codreg, 'fonte': 'mapeamento'}
        return {'sucesso': False, 'erro': f'Região para UF {uf} não encontrada'}

# CLASSE DE INTEGRAÇÃO PARA SERVICE.PY (Wrapper)

class CustomerValidationServiceFinal:
    """
    🎯 INTERFACE PARA INTEGRAÇÃO COM SERVICE.PY
    """
    def __init__(self, parceiros_service):
        self.parceiros_service = parceiros_service
        self.mapping_service = CustomerMappingService(
            token=getattr(parceiros_service, 'token', None),
            parceiros_service=parceiros_service
        )
        print(f"[CUSTOMER VALIDATION FINAL] Serviço inicializado com sucesso")
    
    def processar_cliente_completo(self, dados_cliente_woocommerce: Dict) -> Dict:
        """
        Interface para service.py
        """
        try:
            print(f"[CUSTOMER VALIDATION FINAL] Iniciando processamento completo do cliente...")
            resultado = self.mapping_service.cadastrar_cliente_completo(dados_cliente_woocommerce)
            
            if resultado.get('sucesso'):
                print(f"[CUSTOMER VALIDATION FINAL] SUCESSO COMPLETO!")
                return {
                    'sucesso_geral': True,
                    'codparc_sankhya': resultado.get('codparc'),
                    'nome_parceiro': self._extrair_nome_cliente(dados_cliente_woocommerce),
                    'detalhes': resultado
                }
            else:
                erro_msg = resultado.get('erro', 'Falha desconhecida no mapeamento/cadastro')
                print(f"[CUSTOMER VALIDATION FINAL] ERRO: {erro_msg}")
                return {'sucesso_geral': False, 'erro': erro_msg, 'detalhes': resultado}
            
        except Exception as e:
            print(f"[CUSTOMER VALIDATION FINAL] Exceção: {str(e)}")
            return {'sucesso_geral': False, 'erro': f'Erro crítico no processamento: {str(e)}'}
    
    def _extrair_nome_cliente(self, dados_cliente: Dict) -> str:
        billing = dados_cliente.get('billing', {})
        return f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
