"""
ParceirosService CORRIGIDO E UNIFICADO - Gestão de parceiros/clientes no Sankhya
Versão: 2.7.1 - Aprimora tratamento de endereços, prioriza IDs e corrige extração/consulta,
                garante tipagem correta para inteiros e simplifica retorno para evitar recursão.
"""

from .base import SankhyaClient
from .cidades import CidadesService

class ParceirosService(SankhyaClient):
    """
    Serviço para gestão de parceiros/clientes no Sankhya
    UNIFICADO: Incorpora todas as funcionalidades e correções.
    """
    
    def __init__(self, token=None):
        super().__init__(token)
        # O CidadesService é mantido para buscar CODCID quando não pré-mapeado.
        self.cidades_service = CidadesService(token)
    
    def consultar_por_documento(self, documento):
        """
        Consulta parceiro por documento (CPF/CNPJ).
        CORREÇÃO: Adiciona offsetPage obrigatório e ajusta estrutura de parâmetros.
        """
        if not documento or not documento.strip():
            print("[PARCEIROS] Documento vazio ou inválido.")
            return None

        # Remove formatação do documento
        documento_limpo = documento.replace('.', '').replace('-', '').replace('/', '').strip()
        if not documento_limpo:
            print("[PARCEIROS] Documento limpo está vazio.")
            return None

        print(f"[PARCEIROS] Buscando documento: '{documento}' -> '{documento_limpo}'")

        # CORREÇÃO CRÍTICA: Segue a documentação da API Sankhya para critérios
        criteria = {
            "expression": {
                "$": "this.CGC_CPF = ?"
            },
            "parameter": [
                {
                    "$": documento_limpo, # O valor direto no '$' para parâmetros
                    "type": "S"
                }
            ]
        }

        print(f"[PARCEIROS] Executando consulta com CGC_CPF = '{documento_limpo}'")

        try:
            resultado = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,CGC_CPF,EMAIL,ATIVO",
                criteria=criteria,
                offset_page=0 # CORREÇÃO: offsetPage é obrigatório
            )

            print(f"[PARCEIROS] Resposta status: {resultado.get('status')}")

            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))

            print(f"[PARCEIROS] Total encontrado: {total}")

            if total > 0:
                entity = entities.get("entity")
                if isinstance(entity, list):
                    entity = entity[0] # Pega o primeiro se for uma lista

                # CORREÇÃO: Extração robusta dos campos
                parceiro = {
                    'CODPARC': self._extract_value(entity.get('f0')),
                    'NOMEPARC': self._extract_value(entity.get('f1')),
                    'CGC_CPF': self._extract_value(entity.get('f2')),
                    'EMAIL': self._extract_value(entity.get('f3')),
                    'ATIVO': self._extract_value(entity.get('f4'))
                }

                # VALIDAÇÃO CRÍTICA: Garante que CODPARC seja válido
                codparc = parceiro['CODPARC']
                if not codparc or str(codparc).lower() in ['none', '', '0']:
                    print(f"[PARCEIROS] CODPARC inválido encontrado na resposta: '{codparc}'")
                    return None

                print(f"[PARCEIROS] Encontrado por documento: {codparc} - {parceiro['NOMEPARC']}")
                print(f"[PARCEIROS] CPF/CNPJ: {parceiro['CGC_CPF']} | Email: {parceiro.get('EMAIL', 'N/A')}")
                return parceiro

            print(f"[PARCEIROS] Nenhum parceiro encontrado com documento: {documento_limpo}")
            return None

        except Exception as e:
            print(f"[PARCEIROS] Erro na consulta por documento: {e}")
            return None
    
    def consultar_por_codparc(self, codparc):
        """
        Consulta parceiro por CODPARC.
        """
        if not codparc:
            print("[PARCEIROS] CODPARC vazio ou inválido.")
            return None
            
        try:
            criteria = {
                "expression": {
                    "$": "this.CODPARC = ?"
                },
                "parameter": [
                    {
                        "type": "I", # Tipo inteiro para CODPARC
                        "value": str(codparc)
                    }
                ]
            }
            
            resultado = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,CGC_CPF,EMAIL,ATIVO,TIPPESSOA",
                criteria=criteria,
                offset_page=0 # Garantir offsetPage também aqui
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            if int(entities.get("total", "0")) > 0:
                entity = entities.get("entity")
                if isinstance(entity, list):
                    entity = entity[0]
                
                parceiro = {
                    'CODPARC': self._extract_value(entity.get('f0')),
                    'NOMEPARC': self._extract_value(entity.get('f1')),
                    'CGC_CPF': self._extract_value(entity.get('f2')),
                    'EMAIL': self._extract_value(entity.get('f3')),
                    'ATIVO': self._extract_value(entity.get('f4')),
                    'TIPPESSOA': self._extract_value(entity.get('f5'))
                }
                
                print(f"[PARCEIROS] Parceiro encontrado por CODPARC: {codparc} - {parceiro['NOMEPARC']}")
                return parceiro
            
            print(f"[PARCEIROS] Parceiro não encontrado por CODPARC: {codparc}")
            return None
            
        except Exception as e:
            print(f"[PARCEIROS] Erro na consulta por CODPARC: {e}")
            return None
    
    def consultar_por_email(self, email):
        """
        Consulta parceiro por email.
        """
        if not email or not email.strip():
            print("[PARCEIROS] Email vazio ou inválido.")
            return None
            
        try:
            criteria = {
                "expression": {
                    "$": "this.EMAIL = ?"
                },
                "parameter": [
                    {
                        "type": "S", # Tipo string para email
                        "value": email.strip().lower()
                    }
                ]
            }
            
            resultado = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,CGC_CPF,EMAIL,ATIVO",
                criteria=criteria,
                offset_page=0 # Garantir offsetPage
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            if int(entities.get("total", "0")) > 0:
                entity = entities.get("entity")
                if isinstance(entity, list):
                    entity = entity[0]
                
                parceiro = {
                    'CODPARC': self._extract_value(entity.get('f0')),
                    'NOMEPARC': self._extract_value(entity.get('f1')),
                    'CGC_CPF': self._extract_value(entity.get('f2')),
                    'EMAIL': self._extract_value(entity.get('f3')),
                    'ATIVO': self._extract_value(entity.get('f4'))
                }
                
                print(f"[PARCEIROS] Parceiro encontrado por email: {parceiro['CODPARC']} - {parceiro['NOMEPARC']}")
                return parceiro
            
            print(f"[PARCEIROS] Nenhum parceiro encontrado com email: {email}")
            return None
            
        except Exception as e:
            print(f"[PARCEIROS] Erro na consulta por email: {e}")
            return None
    
    def incluir(self, nome, documento, email=None, telefone=None, endereco_completo=None, **kwargs):
        """
        Inclui novo parceiro no Sankhya, priorizando IDs já mapeados e buscando CODCID se necessário.
        Prioriza kwargs e faz fallback para busca de cidade.
        """
        try:
            documento_limpo = documento.replace('.', '').replace('-', '').replace('/', '').strip()
            tippessoa = 'J' if len(documento_limpo) == 14 else 'F'
            
            dados_parceiro = {
                "NOMEPARC": {"$": str(nome)[:60]},
                "CGC_CPF": {"$": documento_limpo},
                "TIPPESSOA": {"$": tippessoa},
                "ATIVO": {"$": "S"},
                "CLIENTE": {"$": "S"}
            }
            
            if email:
                dados_parceiro["EMAIL"] = {"$": str(email)[:100]}
            
            if telefone:
                telefone_limpo = telefone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '').strip()
                dados_parceiro["TELEFONE"] = {"$": telefone_limpo[:20]}
            
            # CORREÇÃO CRÍTICA: Aplica os kwargs (IDs mapeados) ANTES de qualquer outra lógica.
            # Isso garante que se CODCID, CODEND, CODBAI etc. forem passados, eles serão usados.
            for key, value in kwargs.items():
                if key.upper() not in dados_parceiro and value is not None:
                    # CORREÇÃO: Enviar valores INTEIROS como INTEIROS, não strings, para evitar ORA-00906.
                    # Lista de campos INTEIRO da tabela TGFPAR (do Swagger)
                    integer_fields = ["CODPARC", "CODVEND", "CODPARCMATRIZ", "CODEND", "CODBAI", "CODCID", "CODREG", "RAMAL", "TIMCARTORIO"]
                    if key.upper() in integer_fields:
                        try:
                            # Tenta converter para int. Se falhar, usa como string (fallback)
                            dados_parceiro[key.upper()] = {"$": int(value)}
                            print(f"[PARCEIROS] ℹUsando valor pré-mapeado via kwargs (INTEIRO): {key.upper()} = {value}")
                        except (ValueError, TypeError):
                            dados_parceiro[key.upper()] = {"$": str(value)}
                            print(f"[PARCEIROS] ℹUsando valor pré-mapeado via kwargs (STRING - fallback, valor original: {value}): {key.upper()}")
                    else:
                        dados_parceiro[key.upper()] = {"$": str(value)}
                        print(f"[PARCEIROS] ℹUsando valor pré-mapeado via kwargs (STRING): {key.upper()} = {value}")

            # Lógica de endereço/cidade só executa se os códigos não foram passados via kwargs.
            if endereco_completo and isinstance(endereco_completo, dict):
                # ENDERECO (nome da rua)
                if "CODEND" not in dados_parceiro and endereco_completo.get('address_1'):
                    dados_parceiro["ENDERECO"] = {"$": str(endereco_completo['address_1'])[:60]}
                    print(f"[PARCEIROS] ℹAdicionando ENDERECO (string), CODEND não foi fornecido.")
                elif "CODEND" in dados_parceiro:
                    print(f"[PARCEIROS] ℹCODEND fornecido ({dados_parceiro['CODEND']['$']}), pulando ENDERECO (string).")

                # NUMEND (número) - OBRIGATÓRIO SE ENDERECO COMPLETO FOI PASSADO.
                numend_value = endereco_completo.get('number')
                if "NUMEND" not in dados_parceiro:
                    if numend_value:
                        dados_parceiro["NUMEND"] = {"$": str(numend_value)[:10]}
                        print(f"[PARCEIROS] ℹAdicionando NUMEND: '{dados_parceiro['NUMEND']['$']}'.")
                    else:
                        dados_parceiro["NUMEND"] = {"$": ""}
                        print(f"[PARCEIROS] ℹNUMEND adicionado como vazio (não fornecido).")
                else:
                    print(f"[PARCEIROS] ℹNUMEND já presente via kwargs: '{dados_parceiro['NUMEND']['$']}'.")

                # COMPLEMENTO (opcional)
                if "COMPLEMENTO" not in dados_parceiro and endereco_completo.get('address_2'):
                    dados_parceiro["COMPLEMENTO"] = {"$": str(endereco_completo['address_2'])[:40]}
                    print(f"[PARCEIROS] ℹAdicionando COMPLEMENTO.")

                # BAIRRO (nome do bairro)
                if "CODBAI" not in dados_parceiro and endereco_completo.get('neighborhood'):
                    dados_parceiro["BAIRRO"] = {"$": str(endereco_completo['neighborhood'])[:40]}
                    print(f"[PARCEIROS] ℹAdicionando BAIRRO (string), CODBAI não foi fornecido.")
                elif "CODBAI" in dados_parceiro:
                    print(f"[PARCEIROS] ℹCODBAI fornecido ({dados_parceiro['CODBAI']['$']}), pulando BAIRRO (string).")

                # CEP
                if "CEP" not in dados_parceiro and endereco_completo.get('postcode'):
                    cep_limpo = endereco_completo['postcode'].replace('-', '').replace('.', '').strip()
                    dados_parceiro["CEP"] = {"$": cep_limpo[:8]}
                    print(f"[PARCEIROS] ℹAdicionando CEP.")
                
                # CODCID (city code) - only search if not provided in kwargs
                if "CODCID" not in dados_parceiro:
                    cidade_nome = endereco_completo.get('city', '')
                    uf_sigla = endereco_completo.get('state', '')
                    if cidade_nome and uf_sigla:
                        print(f"[PARCEIROS] CODCID não foi pré-mapeado. Tentando buscar para {cidade_nome}/{uf_sigla} agora...")
                        try:
                            codcid_encontrado = self.cidades_service.obter_codigo_cidade(cidade_nome, uf_sigla) 
                            if codcid_encontrado:
                                # CORREÇÃO: Enviar CODCID como INTEIRO
                                dados_parceiro["CODCID"] = {"$": int(codcid_encontrado)} 
                                print(f"[PARCEIROS] CODCID encontrado: {codcid_encontrado}")
                            else:
                                print(f"[PARCEIROS] CODCID não encontrado para {cidade_nome}/{uf_sigla}. O cadastro pode falhar se CODCID for obrigatório.")
                        except AttributeError:
                             print(f"[PARCEIROS] ERRO FATAL: O método para buscar cidade não foi encontrado em CidadesService. O cadastro pode falhar.")
                             raise AttributeError("O método para buscar o código da cidade não existe ou está nomeado incorretamente no CidadesService.")
                        except Exception as e:
                             print(f"[PARCEIROS] Erro ao buscar código da cidade como fallback: {e}")
                else:
                    print(f"[PARCEIROS] ℹCODCID já presente via kwargs: '{dados_parceiro['CODCID']['$']}'.")

            # Estrutura da requisição (da versão 2.5.1 corrigida)
            payload = {
                "serviceName": "CRUDServiceProvider.saveRecord",
                "requestBody": {
                    "dataSet": {
                        "rootEntity": "Parceiro",
                        "includePresentationFields": "S",
                        # Define os campos que serão enviados no payload. É importante incluir todos
                        # os campos que você está preenchendo em `dados_parceiro`.
                        "entity": {"fieldset": {"list": ",".join(dados_parceiro.keys())}},
                        "dataRow": {"localFields": dados_parceiro} # Usamos dataRow para saveRecord
                    }
                }
            }
            
            print(f"[PARCEIROS] Incluindo parceiro: {nome}")
            print(f"[PARCEIROS] Documento: {documento_limpo} (Tipo: {tippessoa})")
            
            url = self.get_url("CRUDServiceProvider.saveRecord")
            resultado_api = self.post_request(url, payload) # Renomeado para evitar conflito com 'resultado' final
            
            if resultado_api.get("status") == "1":
                # Tenta extrair CODPARC de 'entity' (versão 2.5.1)
                codparc = resultado_api.get("responseBody", {}).get("entities", {}).get("entity", {}).get("CODPARC", {}).get("$")
                if not codparc:
                     # Fallback para extrair de `rows` se a estrutura for diferente (versão 2.5.0)
                     rows = resultado_api.get("responseBody", {}).get("rows", [])
                     if rows:
                         codparc = rows[0].get("CODPARC", {}).get("$")

                if codparc:
                    print(f"[PARCEIROS] Parceiro incluído com sucesso: {codparc}")
                    # CORREÇÃO: Retornar apenas dados essenciais para evitar recursão
                    return {'sucesso': True, 'codparc': codparc}
                else:
                    print(f"[PARCEIROS] Parceiro incluído mas CODPARC não encontrado na resposta. Verifique a resposta do Sankhya.")
                    # CORREÇÃO: Retornar apenas dados essenciais para evitar recursão
                    return {'sucesso': True, 'codparc': None}
            else:
                erro_msg = resultado_api.get("statusMessage", "Erro desconhecido")
                print(f"[PARCEIROS] Erro na inclusão: {erro_msg}")
                # CORREÇÃO: Retornar apenas dados essenciais para evitar recursão
                return {'sucesso': False, 'erro': erro_msg}
                
        except Exception as e:
            print(f"[PARCEIROS] Erro na inclusão do parceiro: {e}")
            # CORREÇÃO: Retornar apenas dados essenciais para evitar recursão
            return {'sucesso': False, 'erro': str(e)}

    def atualizar(self, codparc, dados_atualizacao):
        """
        Atualiza dados de um parceiro existente.
        """
        try:
            # Valida CODPARC
            if not codparc or str(codparc).lower() in ['none', '0', '']:
                raise ValueError(f"CODPARC inválido para atualização: {codparc}")
            
            # Monta dados para atualização
            # O CODPARC é essencial aqui para identificar o registro a ser atualizado
            dados_parceiro = {"CODPARC": {"$": str(codparc)}}
            
            for key, value in dados_atualizacao.items():
                if value is not None:
                    # Garante que as chaves sejam maiúsculas para o Sankhya
                    # E garante que inteiros sejam enviados como int, não string
                    integer_fields = ["CODPARC", "CODVEND", "CODPARCMATRIZ", "CODEND", "CODBAI", "CODCID", "CODREG", "RAMAL", "TIMCARTORIO"]
                    if key.upper() in integer_fields:
                        try:
                            dados_parceiro[key.upper()] = {"$": int(value)}
                        except (ValueError, TypeError):
                            dados_parceiro[key.upper()] = {"$": str(value)} # Fallback
                    else:
                        dados_parceiro[key.upper()] = {"$": str(value)}
            
            payload = {
                "serviceName": "CRUDServiceProvider.saveRecord",
                "requestBody": {
                    "dataSet": {
                        "rootEntity": "Parceiro",
                        "includePresentationFields": "S",
                        # Garante que o fieldset inclua o CODPARC e todos os campos a serem atualizados
                        "entity": {
                            "fieldset": {
                                "list": ",".join(dados_parceiro.keys())
                            }
                        },
                        "dataRow": {"localFields": dados_parceiro} # Usa dataRow para saveRecord
                    }
                }
            }
            
            print(f"[PARCEIROS] Solicitando atualização para parceiro: {codparc}")
            print(f"[PARCEIROS] Dados de atualização: {dados_atualizacao}")
            
            url = self.get_url("CRUDServiceProvider.saveRecord")
            resultado = self.post_request(url, payload)
            
            if resultado.get("status") == "1":
                print(f"[PARCEIROS] Parceiro atualizado com sucesso: {codparc}")
                return {
                    'sucesso': True,
                    'codparc': codparc # Mantém o codparc para referência
                }
            else:
                erro_msg = resultado.get("statusMessage", "Erro desconhecido")
                print(f"[PARCEIROS] Erro na atualização: {erro_msg}")
                
                return {
                    'sucesso': False,
                    'erro': erro_msg
                }
                
        except Exception as e:
            print(f"[PARCEIROS] Erro na atualização do parceiro: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def desativar(self, codparc, motivo=None):
        """
        Desativa um parceiro no Sankhya.
        """
        print(f"[PARCEIROS] ⏳ Tentando desativar parceiro: {codparc}")
        # Reutiliza o método de atualização para desativar.
        observacao = f"Desativado: {motivo}" if motivo else "Desativado via integração"
        return self.atualizar(codparc, {"ATIVO": "N", "OBSERVACAO": observacao})
    
    def reativar(self, codparc):
        """
        Reativa um parceiro no Sankhya.
        """
        print(f"[PARCEIROS] ⏳ Tentando reativar parceiro: {codparc}")
        # Reutiliza o método de atualização para reativar.
        return self.atualizar(codparc, {"ATIVO": "S", "OBSERVACAO": "Reativado via integração"})
    
    def listar_ativos(self, limite=50):
        """
        Lista parceiros ativos (clientes) no Sankhya.
        """
        try:
            criteria = {
                "expression": {
                    "$": "this.ATIVO = ? AND this.CLIENTE = ?"
                },
                "parameter": [
                    {"type": "S", "value": "S"},
                    {"type": "S", "value": "S"}
                ]
            }
            
            resultado = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,CGC_CPF,EMAIL",
                criteria=criteria,
                limit=limite,
                offset_page=0 # Garantir offsetPage
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                parceiros = []
                for entity in entity_list:
                    parceiro = {
                        'CODPARC': self._extract_value(entity.get('f0')),
                        'NOMEPARC': self._extract_value(entity.get('f1')),
                        'CGC_CPF': self._extract_value(entity.get('f2')),
                        'EMAIL': self._extract_value(entity.get('f3'))
                    }
                    parceiros.append(parceiro)
                
                print(f"[PARCEIROS] Encontrados {total} parceiros ativos.")
                return {
                    'total': total,
                    'parceiros': parceiros
                }
            
            print("[PARCEIROS] Nenhum parceiro ativo encontrado.")
            return {'total': 0, 'parceiros': []}
            
        except Exception as e:
            print(f"[PARCEIROS] Erro ao listar parceiros ativos: {e}")
            return {'total': 0, 'parceiros': [], 'erro': str(e)}
    
    def listar_todos(self, limite=100, filtros=None):
        """
        Lista todos os parceiros com filtros opcionais no Sankhya.
        """
        try:
            # Monta critérios de busca
            expression_parts = []
            parameters = []
            
            if filtros:
                if 'ativo' in filtros and filtros['ativo'] is not None:
                    expression_parts.append("this.ATIVO = ?")
                    parameters.append({"type": "S", "value": "S" if filtros['ativo'] else "N"})
                
                if 'cliente' in filtros and filtros['cliente'] is not None:
                    expression_parts.append("this.CLIENTE = ?")
                    parameters.append({"type": "S", "value": "S" if filtros['cliente'] else "N"})
                
                if 'fornecedor' in filtros and filtros['fornecedor'] is not None:
                    expression_parts.append("this.FORNECEDOR = ?")
                    parameters.append({"type": "S", "value": "S" if filtros['fornecedor'] else "N"})
                
                if filtros.get('tippessoa'):
                    expression_parts.append("this.TIPPESSOA = ?")
                    parameters.append({"type": "S", "value": filtros['tippessoa']})
                
                if filtros.get('nome_contem'):
                    expression_parts.append("this.NOMEPARC LIKE ?")
                    parameters.append({"type": "S", "value": f"%{filtros['nome_contem']}%"})
                
                if filtros.get('documento'):
                    documento_limpo = filtros['documento'].replace('.', '').replace('-', '').replace('/', '').strip()
                    if documento_limpo:
                        expression_parts.append("this.CGC_CPF = ?")
                        parameters.append({"type": "S", "value": documento_limpo})

            # Se não há filtros específicos, busca todos os clientes ativos por padrão.
            if not expression_parts:
                expression_parts = ["this.CLIENTE = ?", "this.ATIVO = ?"]
                parameters = [
                    {"type": "S", "value": "S"},
                    {"type": "S", "value": "S"}
                ]
            
            criteria = {
                "expression": {
                    "$": " AND ".join(expression_parts) if expression_parts else "1=1" # Garante que a expressão não seja vazia
                },
                "parameter": parameters
            }
            
            resultado = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,CGC_CPF,EMAIL,ATIVO,TIPPESSOA,CLIENTE,FORNECEDOR",
                criteria=criteria,
                limit=limite,
                offset_page=0 # Garantir offsetPage
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                parceiros = []
                for entity in entity_list:
                    parceiro = {
                        'CODPARC': self._extract_value(entity.get('f0')),
                        'NOMEPARC': self._extract_value(entity.get('f1')),
                        'CGC_CPF': self._extract_value(entity.get('f2')),
                        'EMAIL': self._extract_value(entity.get('f3')),
                        'ATIVO': self._extract_value(entity.get('f4')),
                        'TIPPESSOA': self._extract_value(entity.get('f5')),
                        'CLIENTE': self._extract_value(entity.get('f6')),
                        'FORNECEDOR': self._extract_value(entity.get('f7'))
                    }
                    parceiros.append(parceiro)
                
                print(f"[PARCEIROS] Encontrados {total} parceiros com filtros aplicados.")
                return {
                    'total': total,
                    'parceiros': parceiros,
                    'filtros_aplicados': filtros
                }
            
            print("[PARCEIROS] Nenhum parceiro encontrado com os filtros aplicados.")
            return {'total': 0, 'parceiros': [], 'filtros_aplicados': filtros}
            
        except Exception as e:
            print(f"[PARCEIROS] Erro ao listar todos os parceiros: {e}")
            return {'total': 0, 'parceiros': [], 'erro': str(e)}
    
    def buscar_por_nome(self, nome, limite=20):
        """
        Busca parceiros por nome (busca parcial) no Sankhya.
        """
        try:
            if not nome or len(nome.strip()) < 3:
                print("[PARCEIROS] Nome para busca deve ter pelo menos 3 caracteres.")
                return {'total': 0, 'parceiros': [], 'erro': 'Nome deve ter pelo menos 3 caracteres'}
            
            criteria = {
                "expression": {
                    "$": "this.NOMEPARC LIKE ? AND this.ATIVO = ?"
                },
                "parameter": [
                    {"type": "S", "value": f"%{nome.strip()}%"},
                    {"type": "S", "value": "S"}
                ]
            }
            
            resultado = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC,CGC_CPF,EMAIL",
                criteria=criteria,
                limit=limite,
                offset_page=0 # Garantir offsetPage
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                parceiros = []
                for entity in entity_list:
                    parceiro = {
                        'CODPARC': self._extract_value(entity.get('f0')),
                        'NOMEPARC': self._extract_value(entity.get('f1')),
                        'CGC_CPF': self._extract_value(entity.get('f2')),
                        'EMAIL': self._extract_value(entity.get('f3'))
                    }
                    parceiros.append(parceiro)
                
                print(f"[PARCEIROS] Encontrados {total} parceiros com nome contendo '{nome}'")
                return {
                    'total': total,
                    'parceiros': parceiros,
                    'termo_busca': nome
                }
            
            print(f"[PARCEIROS] Nenhum parceiro encontrado com nome contendo '{nome}'")
            return {'total': 0, 'parceiros': [], 'termo_busca': nome}
            
        except Exception as e:
            print(f"[PARCEIROS] Erro na busca por nome: {e}")
            return {'total': 0, 'parceiros': [], 'erro': str(e)}
    
    def obter_enderecos(self, codparc):
        """
        Obtém endereços de um parceiro no Sankhya.
        """
        if not codparc:
            print("[PARCEIROS] CODPARC vazio para obter endereços.")
            return {'encontrado': False, 'total': 0, 'enderecos': [], 'erro': 'CODPARC inválido'}

        try:
            criteria = {
                "expression": {
                    "$": "this.CODPARC = ?"
                },
                "parameter": [
                    {
                        "type": "I",
                        "value": str(codparc)
                    }
                ]
            }
            
            resultado = self.load_records(
                entity="EnderecosParceiro", # Nome da entidade no Sankhya para endereços de parceiro
                fields="CODEND,ENDERECO,NUMEND,COMPLEMENTO,BAIRRO,CEP,CODCID",
                criteria=criteria,
                offset_page=0 # Garantir offsetPage
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                enderecos = []
                for entity in entity_list:
                    endereco = {
                        'CODEND': self._extract_value(entity.get('f0')),
                        'ENDERECO': self._extract_value(entity.get('f1')),
                        'NUMEND': self._extract_value(entity.get('f2')),
                        'COMPLEMENTO': self._extract_value(entity.get('f3')),
                        'BAIRRO': self._extract_value(entity.get('f4')),
                        'CEP': self._extract_value(entity.get('f5')),
                        'CODCID': self._extract_value(entity.get('f6'))
                    }
                    enderecos.append(endereco)
                
                print(f"[PARCEIROS] Encontrados {total} endereços para o parceiro {codparc}.")
                return {
                    'encontrado': True,
                    'total': total,
                    'enderecos': enderecos
                }
            
            print(f"[PARCEIROS] Nenhum endereço encontrado para o parceiro {codparc}.")
            return {'encontrado': False, 'total': 0, 'enderecos': []}
            
        except Exception as e:
            print(f"[PARCEIROS] Erro ao obter endereços para o parceiro {codparc}: {e}")
            return {'encontrado': False, 'erro': str(e)}
    
    def obter_contatos(self, codparc):
        """
        Obtém contatos de um parceiro no Sankhya.
        """
        if not codparc:
            print("[PARCEIROS] CODPARC vazio para obter contatos.")
            return {'encontrado': False, 'total': 0, 'contatos': [], 'erro': 'CODPARC inválido'}

        try:
            criteria = {
                "expression": {
                    "$": "this.CODPARC = ?"
                },
                "parameter": [
                    {
                        "type": "I",
                        "value": str(codparc)
                    }
                ]
            }
            
            resultado = self.load_records(
                entity="Contato", # Nome da entidade no Sankhya para contatos
                fields="CODCONTATO,NOMECONTATO,EMAIL,TELEFONE,CELULAR",
                criteria=criteria,
                offset_page=0 # Garantir offsetPage
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                contatos = []
                for entity in entity_list:
                    contato = {
                        'CODCONTATO': self._extract_value(entity.get('f0')),
                        'NOMECONTATO': self._extract_value(entity.get('f1')),
                        'EMAIL': self._extract_value(entity.get('f2')),
                        'TELEFONE': self._extract_value(entity.get('f3')),
                        'CELULAR': self._extract_value(entity.get('f4'))
                    }
                    contatos.append(contato)
                
                print(f"[PARCEIROS] Encontrados {total} contatos para o parceiro {codparc}.")
                return {
                    'encontrado': True,
                    'total': total,
                    'contatos': contatos
                }
            
            print(f"[PARCEIROS] Nenhum contato encontrado para o parceiro {codparc}.")
            return {'encontrado': False, 'total': 0, 'contatos': []}
            
        except Exception as e:
            print(f"[PARCEIROS] Erro ao obter contatos para o parceiro {codparc}: {e}")
            return {'encontrado': False, 'erro': str(e)}
    
    def validar_documento(self, documento):
        """
        Valida CPF ou CNPJ.
        Função utilitária que não interage com o Sankhya.
        """
        try:
            documento_limpo = documento.replace('.', '').replace('-', '').replace('/', '').strip()
            
            if len(documento_limpo) == 11:
                # Validação de CPF
                return self._validar_cpf(documento_limpo)
            elif len(documento_limpo) == 14:
                # Validação de CNPJ
                return self._validar_cnpj(documento_limpo)
            else:
                return {
                    'valido': False,
                    'tipo': 'desconhecido',
                    'erro': 'Documento deve ter 11 (CPF) ou 14 (CNPJ) dígitos para validação básica.'
                }
                
        except Exception as e:
            print(f"[PARCEIROS] Erro na validação de documento: {e}")
            return {
                'valido': False,
                'erro': str(e)
            }
    
    def _validar_cpf(self, cpf):
        """
        Valida o formato de um CPF.
        Método interno utilitário.
        """
        # Remove caracteres não numéricos
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Verifica se tem 11 dígitos
        if len(cpf) != 11:
            return {'valido': False, 'tipo': 'CPF', 'erro': 'CPF deve ter 11 dígitos.'}
        
        # Verifica se não são todos iguais (CPFs inválidos comuns)
        if cpf == cpf[0] * 11:
            return {'valido': False, 'tipo': 'CPF', 'erro': 'CPF inválido (dígitos repetidos).'}
        
        # Cálculo do primeiro dígito verificador
        soma = 0
        for i in range(9):
            soma += int(cpf[i]) * (10 - i)
        digito1 = (soma * 10) % 11
        if digito1 == 10:
            digito1 = 0
        
        # Cálculo do segundo dígito verificador
        soma = 0
        for i in range(10):
            soma += int(cpf[i]) * (11 - i)
        digito2 = (soma * 10) % 11
        if digito2 == 10:
            digito2 = 0
        
        if int(cpf[9]) == digito1 and int(cpf[10]) == digito2:
            return {'valido': True, 'tipo': 'CPF'}
        else:
            return {'valido': False, 'tipo': 'CPF', 'erro': 'CPF inválido (dígitos verificadores incorretos).'}
                
    def _validar_cnpj(self, cnpj):
        """
        Valida o formato de um CNPJ.
        Método interno utilitário.
        """
        # Remove caracteres não numéricos
        cnpj = ''.join(filter(str.isdigit, cnpj))
        
        # Verifica se tem 14 dígitos
        if len(cnpj) != 14:
            return {'valido': False, 'tipo': 'CNPJ', 'erro': 'CNPJ deve ter 14 dígitos.'}
        
        # Verifica se não são todos iguais (CNPJs inválidos comuns)
        if cnpj == cnpj[0] * 14:
            return {'valido': False, 'tipo': 'CNPJ', 'erro': 'CNPJ inválido (dígitos repetidos).'}
        
        # Cálculo do primeiro dígito verificador
        tamanho = len(cnpj) - 2
        soma = 0
        pos = tamanho - 7
        for i in range(tamanho):
            soma += int(cnpj[i]) * pos
            pos -= 1
            if pos < 2:
                pos = 9
        digito1 = 11 - (soma % 11)
        if digito1 > 9:
            digito1 = 0
        
        # Cálculo do segundo dígito verificador
        tamanho = len(cnpj) - 1
        soma = 0
        pos = tamanho - 7
        for i in range(tamanho):
            soma += int(cnpj[i]) * pos
            pos -= 1
            if pos < 2:
                pos = 9
        digito2 = 11 - (soma % 11)
        if digito2 > 9:
            digito2 = 0
        
        # Pesos para cálculo do CNPJ
        pesos_cnpj = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] # Definição local para o método
        
        if int(cnpj[12]) == digito1 and int(cnpj[13]) == digito2:
            return {'valido': True, 'tipo': 'CNPJ'}
        else:
            return {'valido': False, 'tipo': 'CNPJ', 'erro': 'CNPJ inválido (dígitos verificadores incorretos).'}

    def _extract_value(self, field_obj):
        """
        Extrai o valor de um objeto de campo retornado pelo Sankhya de forma robusta.
        CORRIGIDO: Trata None, dicionários com '$' e outros tipos.
        """
        if not field_obj:
            return ""
        
        if isinstance(field_obj, dict):
            # Tenta extrair de '$' que é o padrão para valores simples
            return field_obj.get('$', '')
        
        # Converte para string se não for None e não for um dicionário
        return str(field_obj) if field_obj is not None else ""
