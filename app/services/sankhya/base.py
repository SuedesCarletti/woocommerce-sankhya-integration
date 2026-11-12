"""
SankhyaClient CORRIGIDO - Cliente base para API do Sankhya
Versão: 2.5.0 - Versão completamente corrigida sem erros de sintaxe
"""

import requests
from config.settings import load_config

class SankhyaClient:
    """
    Cliente base para API do Sankhya - VERSÃO CORRIGIDA
    """
    
    def __init__(self, token=None):
        self.config = load_config()
        self.token = token
        self.base_url = self.config['SANKHYA_BASE_URL']
        self.appkey = self.config['SANKHYA_APPKEY']
    
    def get_headers(self):
        """Headers padrão para requisições"""
        headers = {
            'Content-Type': 'application/json',
            'appkey': self.appkey
        }
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        return headers
    
    def get_url(self, service_name):
        """Constrói URL para serviços MGE"""
        return f"{self.base_url}/gateway/v1/mge/service.sbr?serviceName={service_name}&outputType=json"
    
    def get_commerce_url(self, service_name):
        """Constrói URL para serviços MGECOM"""
        return f"{self.base_url}/gateway/v1/mgecom/service.sbr?serviceName={service_name}&outputType=json"
    
    def post_request(self, url, payload):
        """
        Faz requisição POST usando token de autenticação
        """
        headers = self.get_headers()
        
        try:
            print(f"[SANKHYA] POST {url}")
            
            if not self.token:
                raise ValueError("Token de autenticação não disponível")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            print(f"[SANKHYA] {url} - Status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            sankhya_status = result.get("status", "unknown")
            if sankhya_status == "1":
                print(f"[SANKHYA] Sucesso no Sankhya")
            else:
                status_msg = result.get("statusMessage", "Erro não especificado")
                print(f"[SANKHYA] Erro no Sankhya: {status_msg}")
            
            return result
            
        except requests.exceptions.Timeout:
            print(f"[SANKHYA] ⏰ Timeout na requisição para {url}")
            raise
        except requests.exceptions.HTTPError as e:
            print(f"[SANKHYA] Erro HTTP {response.status_code}: {e}")
            print(f"[SANKHYA] Response: {response.text}")
            raise
        except Exception as e:
            print(f"[SANKHYA] Erro na requisição: {e}")
            raise
    
    def get_request(self, url, params=None):
        """
        Faz requisição GET
        """
        headers = self.get_headers()
        
        try:
            print(f"[SANKHYA] GET {url}")
            
            if not self.token:
                raise ValueError("Token de autenticação não disponível")
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            print(f"[SANKHYA] {url} - Status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            sankhya_status = result.get("status", "unknown")
            if sankhya_status == "1":
                print(f"[SANKHYA] Sucesso no Sankhya")
            else:
                status_msg = result.get("statusMessage", "Erro não especificado")
                print(f"[SANKHYA] Erro no Sankhya: {status_msg}")
            
            return result
            
        except requests.exceptions.Timeout:
            print(f"[SANKHYA] ⏰ Timeout na requisição GET para {url}")
            raise
        except requests.exceptions.HTTPError as e:
            print(f"[SANKHYA] Erro HTTP GET {response.status_code}: {e}")
            raise
        except Exception as e:
            print(f"[SANKHYA] Erro na requisição GET: {e}")
            raise
    
    def load_records(self, entity, fields=None, criteria=None, limit=None, offset_page=None):
        """
        ✅ CORRIGIDO: Adiciona suporte ao offsetPage obrigatório
        """
        payload = {
            "serviceName": "CRUDServiceProvider.loadRecords",
            "requestBody": {
                "dataSet": {
                    "rootEntity": entity,
                    "includePresentationFields": "S"
                }
            }
        }

        # CORREÇÃO PRINCIPAL: offsetPage sempre obrigatório
        if offset_page is not None:
            payload["requestBody"]["dataSet"]["offsetPage"] = str(offset_page)
        else:
            payload["requestBody"]["dataSet"]["offsetPage"] = "0"  # ← PADRÃO: página 0

        # Adiciona campos se especificados
        if fields:
            payload["requestBody"]["dataSet"]["entity"] = {
                "fieldset": {
                    "list": fields
                }
            }

        # Adiciona critérios se especificados
        if criteria:
            payload["requestBody"]["dataSet"]["criteria"] = criteria

        # Adiciona limite se especificado
        if limit:
            payload["requestBody"]["dataSet"]["limit"] = str(limit)

        url = self.get_url("CRUDServiceProvider.loadRecords")
        return self.post_request(url, payload)
    
    def save_record(self, entity, dados, codpk=None):
        """
        Salva registro usando CRUDServiceProvider.saveRecord
        """
        try:
            if codpk is None or str(codpk) == "0":
                print(f"[SANKHYA] Incluindo novo registro em {entity}")
            else:
                print(f"[SANKHYA] Atualizando registro {codpk} em {entity}")
            
            row_data = {}
            if codpk is not None:
                pk_field = self._get_pk_field(entity)
                row_data[pk_field] = {"$": str(codpk)}
            
            for key, value in dados.items():
                if isinstance(value, dict) and "$" in value:
                    row_data[key] = value
                else:
                    row_data[key] = {"$": str(value) if value is not None else ""}
            
            payload = {
                "serviceName": "CRUDServiceProvider.saveRecord",
                "requestBody": {
                    "dataSet": {
                        "rootEntity": entity,
                        "includePresentationFields": "S",
                        "entity": {
                            "fieldset": {
                                "list": ",".join(row_data.keys())
                            }
                        },
                        "rows": [row_data]
                    }
                }
            }
            
            url = self.get_url("CRUDServiceProvider.saveRecord")
            return self.post_request(url, payload)
            
        except Exception as e:
            print(f"[SANKHYA] Erro ao salvar registro: {e}")
            return {
                "status": "0",
                "statusMessage": str(e)
            }
    
    def delete_record(self, entity, codpk):
        """
        Remove um registro
        """
        try:
            pk_field = self._get_pk_field(entity)
            
            payload = {
                "serviceName": "CRUDServiceProvider.removeRecord",
                "requestBody": {
                    "dataSet": {
                        "rootEntity": entity,
                        "entity": {
                            "fieldset": {
                                "list": pk_field
                            }
                        },
                        "rows": [{
                            pk_field: {"$": str(codpk)}
                        }]
                    }
                }
            }
            
            print(f"[SANKHYA] Removendo registro {codpk} de {entity}")
            
            url = self.get_url("CRUDServiceProvider.removeRecord")
            resultado = self.post_request(url, payload)
            
            if resultado.get("status") == "1":
                print(f"[SANKHYA] Registro removido com sucesso")
                return {
                    'sucesso': True,
                    'entity': entity,
                    'codpk': codpk,
                    'dados_resposta': resultado
                }
            else:
                erro_msg = resultado.get("statusMessage", "Erro desconhecido")
                print(f"[SANKHYA] Erro na remoção: {erro_msg}")
                
                return {
                    'sucesso': False,
                    'erro': erro_msg,
                    'dados_resposta': resultado
                }
                
        except Exception as e:
            print(f"[SANKHYA] Erro ao remover registro: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def execute_query(self, sql: str) -> dict:
        """
        Executa SQL direto via DbExplorerSP.executeQuery.
        Necessário para campos CLOB (XML, XMLENVCLI) que o loadRecords
        não retorna corretamente (total=0 silencioso).
        """
        url = self.get_url("DbExplorerSP.executeQuery")
        payload = {
            "serviceName": "DbExplorerSP.executeQuery",
            "requestBody": {
                "sql": sql
            }
        }
        print(f"[SANKHYA] SQL: {sql[:120]}...")
        return self.post_request(url, payload)

    def execute_service(self, service_name, parameters=None):
        """
        Executa um serviço específico do Sankhya
        """
        try:
            request_body = {}
            
            if parameters:
                request_body.update(parameters)
            
            payload = {
                "serviceName": service_name,
                "requestBody": request_body
            }
            
            print(f"[SANKHYA] Executando serviço: {service_name}")
            
            url = self.get_url(service_name)
            resultado = self.post_request(url, payload)
            
            if resultado.get("status") == "1":
                print(f"[SANKHYA] Serviço executado com sucesso")
            else:
                erro_msg = resultado.get("statusMessage", "Erro desconhecido")
                print(f"[SANKHYA] Erro no serviço: {erro_msg}")
            
            return resultado
            
        except Exception as e:
            print(f"[SANKHYA] Erro ao executar serviço: {e}")
            return {
                "status": "0",
                "statusMessage": str(e)
            }
    
    def execute_commerce_service(self, service_name, parameters=None):
        """
        Executa um serviço de comércio do Sankhya
        """
        try:
            request_body = {}
            
            if parameters:
                request_body.update(parameters)
            
            payload = {
                "serviceName": service_name,
                "requestBody": request_body
            }
            
            print(f"[SANKHYA] Executando serviço de comércio: {service_name}")
            
            url = self.get_commerce_url(service_name)
            resultado = self.post_request(url, payload)
            
            if resultado.get("status") == "1":
                print(f"[SANKHYA] Serviço de comércio executado com sucesso")
            else:
                erro_msg = resultado.get("statusMessage", "Erro desconhecido")
                print(f"[SANKHYA] Erro no serviço de comércio: {erro_msg}")
            
            return resultado
            
        except Exception as e:
            print(f"[SANKHYA] Erro ao executar serviço de comércio: {e}")
            return {
                "status": "0",
                "statusMessage": str(e)
            }
    
    def _get_pk_field(self, entity):
        """
        Retorna o nome do campo chave primária baseado na entidade
        """
        pk_mapping = {
            "Parceiro": "CODPARC",
            "CabecalhoNota": "NUNOTA",
            "ItemNota": "NUITEM",
            "Produto": "CODPROD",
            "Cidade": "CODCID",
            "Contato": "CODCONTATO",
            "Empresa": "CODEMP",
            "Usuario": "CODUSU",
            "TipoOperacao": "CODTIPOPER",
            "TipoNegociacao": "CODTIPVENDA",
            "Vendedor": "CODVEND",
            "LocalEstoque": "CODLOCAL",
            "UnidadeMedida": "CODVOL"
        }
        
        return pk_mapping.get(entity, "ID")
    
    def validar_conexao(self):
        """
        Testa se a conexão com Sankhya está funcionando
        """
        try:
            if not self.token:
                return {
                    'conectado': False,
                    'erro': 'Token não disponível'
                }
            
            resultado = self.load_records(
                entity="Parceiro",
                fields="CODPARC,NOMEPARC",
                limit=1
            )
            
            if resultado.get("status") == "1":
                return {
                    'conectado': True,
                    'mensagem': 'Conexão com Sankhya OK'
                }
            else:
                return {
                    'conectado': False,
                    'erro': resultado.get("statusMessage", "Erro na consulta")
                }
                
        except Exception as e:
            return {
                'conectado': False,
                'erro': str(e)
            }
    
    def obter_info_sessao(self):
        """
        Retorna informações sobre a sessão atual
        """
        return {
            'token_disponivel': bool(self.token),
            'base_url': self.base_url,
            'appkey_configurado': bool(self.appkey),
            'headers': self.get_headers() if self.token else None
        }
    
    def testar_autenticacao(self):
        """
        Testa se a autenticação está funcionando
        """
        try:
            if not self.token:
                return {
                    'autenticado': False,
                    'erro': 'Token não disponível'
                }
            
            headers = self.get_headers()
            url = self.get_url("CRUDServiceProvider.loadRecords")
            
            payload = {
                "serviceName": "CRUDServiceProvider.loadRecords",
                "requestBody": {
                    "dataSet": {
                        "rootEntity": "Empresa",
                        "includePresentationFields": "S",
                        "entity": {
                            "fieldset": {
                                "list": "CODEMP,RAZAOSOCIAL"
                            }
                        },
                        "offsetPage": "0",
                        "countPage": "1"
                    }
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "1":
                    return {
                        'autenticado': True,
                        'mensagem': 'Autenticação válida'
                    }
                else:
                    return {
                        'autenticado': False,
                        'erro': result.get("statusMessage", "Erro na autenticação")
                    }
            else:
                return {
                    'autenticado': False,
                    'erro': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                'autenticado': False,
                'erro': str(e)
            }
    
    def obter_configuracao_sistema(self):
        """
        Obtém configurações do sistema Sankhya
        """
        try:
            resultado = self.load_records(
                entity="Empresa",
                fields="CODEMP,RAZAOSOCIAL,NOMEFANTASIA,CGC_CPF",
                limit=10
            )
            
            if resultado.get("status") == "1":
                entities = resultado.get("responseBody", {}).get("entities", {})
                total = int(entities.get("total", "0"))
                
                empresas = []
                if total > 0:
                    entity_list = entities.get("entity", [])
                    if not isinstance(entity_list, list):
                        entity_list = [entity_list]
                    
                    for entity in entity_list:
                        empresa = {
                            'CODEMP': self._extract_value(entity.get('f0')),
                            'RAZAOSOCIAL': self._extract_value(entity.get('f1')),
                            'NOMEFANTASIA': self._extract_value(entity.get('f2')),
                            'CGC_CPF': self._extract_value(entity.get('f3'))
                        }
                        empresas.append(empresa)
                
                return {
                    'sucesso': True,
                    'total_empresas': total,
                    'empresas': empresas,
                    'token_valido': True
                }
            else:
                return {
                    'sucesso': False,
                    'erro': resultado.get("statusMessage", "Erro ao obter configurações")
                }
                
        except Exception as e:
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def _extract_value(self, field_obj):
        """
        Extrai valor do objeto de campo do Sankhya
        """
        if not field_obj:
            return ""
        
        if isinstance(field_obj, dict):
            return field_obj.get('$', '')
        
        return str(field_obj) if field_obj is not None else ""
    
    def formatar_data_sankhya(self, data):
        """
        Formata data para o padrão do Sankhya (DD/MM/AAAA)
        """
        try:
            from datetime import datetime

            if isinstance(data, str):
                formatos = [
                    '%Y-%m-%d',      # 2025-06-17
                    '%d/%m/%Y',      # 17/06/2025
                    '%Y-%m-%d %H:%M:%S',
                    '%d/%m/%Y %H:%M:%S'
                ]

                for formato in formatos:
                    try:
                        data_obj = datetime.strptime(data, formato)
                        return data_obj.strftime('%d/%m/%Y')
                    except ValueError:
                        continue

                raise ValueError(f"Formato de data não reconhecido: {data}")

            elif hasattr(data, 'strftime'):
                return data.strftime('%d/%m/%Y')
            else:
                raise ValueError(f"Tipo de data não suportado: {type(data)}")

        except Exception as e:
            print(f"[SANKHYA] Erro ao formatar data: {e}")
            from datetime import datetime
            return datetime.now().strftime('%d/%m/%Y')  # Fallback para hoje
      
    def formatar_valor_sankhya(self, valor):
        """
        Formata valor numérico para o padrão do Sankhya
        """
        try:
            if valor is None:
                return "0"
            
            if isinstance(valor, str):
                valor = valor.replace('.', '').replace(',', '.')
            
            valor_float = float(valor)
            return f"{valor_float:.2f}"
            
        except Exception as e:
            print(f"[SANKHYA] Erro ao formatar valor: {e}")
            return "0.00"
