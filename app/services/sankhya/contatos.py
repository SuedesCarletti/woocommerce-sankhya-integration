from .base import SankhyaClient

class ContatosService(SankhyaClient):
    """
    Serviço para gestão de contatos no Sankhya
    VERSÃO CORRIGIDA: Validação rigorosa de parâmetros para evitar "param[0] = null"
    """
    
    def consultar_por_parceiro(self, codparc):
        """
        Consulta contatos com validação rigorosa de parâmetros
        """
        if not codparc:
            print(f"[CONTATOS] CODPARC está vazio")
            return []
        
        # CORREÇÃO: Validação rigorosa do parâmetro
        try:
            codparc_int = int(codparc)
            if codparc_int <= 0:
                print(f"[CONTATOS] CODPARC inválido: {codparc}")
                return []
        except (ValueError, TypeError):
            print(f"[CONTATOS] CODPARC não é número válido: {codparc}")
            return []
        
        criteria = {
            "expression": {"$": "this.CODPARC = ?"},
            "parameter": [{
                "type": "I",
                "$": str(codparc_int)  # CORREÇÃO: Usar valor validado e formato correto
            }]
        }
        
        try:
            print(f"[CONTATOS] Consultando contatos para parceiro: {codparc_int}")
            
            result = self.load_records(
                entity="Contato",
                fields="CODPARC,CODCONTATO,NOMECONTATO,TELEFONE,EMAIL",
                criteria=criteria
            )
            
            # CORREÇÃO: Verificar status antes de processar
            if result.get("status") == "0":
                error_msg = result.get("statusMessage", "Erro desconhecido")
                print(f"[CONTATOS] Erro do Sankhya: {error_msg}")
                return []
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total == 0:
                print(f"[CONTATOS] Nenhum contato encontrado para parceiro {codparc_int}")
                return []
            
            # Se há apenas um contato
            if total == 1:
                entity = entities.get("entity", {})
                contato = {
                    "CODPARC": entity["f0"]["$"],
                    "CODCONTATO": entity["f1"]["$"],
                    "NOMECONTATO": entity["f2"]["$"],
                    "TELEFONE": entity["f3"]["$"],
                    "EMAIL": entity["f4"]["$"]
                }
                return [contato]
            
            # Se há múltiplos contatos
            contatos = []
            for entity in entities.get("entity", []):
                contato = {
                    "CODPARC": entity["f0"]["$"],
                    "CODCONTATO": entity["f1"]["$"],
                    "NOMECONTATO": entity["f2"]["$"],
                    "TELEFONE": entity["f3"]["$"],
                    "EMAIL": entity["f4"]["$"]
                }
                contatos.append(contato)
            
            print(f"[CONTATOS] Encontrados {len(contatos)} contatos para parceiro {codparc_int}")
            return contatos
            
        except Exception as e:
            print(f"[CONTATOS] Erro na consulta: {e}")
            return []
    
    def consultar_contato_por_nome_email(self, codparc, nome_contato, email=None):
        """
        Consulta contato específico com validação
        """
        if not codparc:
            print(f"[CONTATOS] CODPARC vazio para busca por nome/email")
            return None
            
        # CORREÇÃO: Validação do CODPARC
        try:
            codparc_int = int(codparc)
            if codparc_int <= 0:
                print(f"[CONTATOS] CODPARC inválido: {codparc}")
                return None
        except (ValueError, TypeError):
            print(f"[CONTATOS] CODPARC não numérico: {codparc}")
            return None
        
        if not nome_contato and not email:
            print(f"[CONTATOS] Nome e email vazios")
            return None
        
        # Busca todos os contatos do parceiro (método já corrigido)
        contatos_existentes = self.consultar_por_parceiro(codparc_int)
        
        for contato in contatos_existentes:
            # Verifica por nome (case insensitive)
            if nome_contato and contato['NOMECONTATO'].upper().strip() == nome_contato.upper().strip():
                print(f"[CONTATOS] Contato encontrado por nome: {contato['CODCONTATO']} - {contato['NOMECONTATO']}")
                return contato
            
            # Verifica por email se fornecido
            if email and contato['EMAIL'].upper().strip() == email.upper().strip():
                print(f"[CONTATOS] Contato encontrado por email: {contato['CODCONTATO']} - {contato['EMAIL']}")
                return contato
        
        return None
    
    def cadastrar(self, codparc, nome_contato, telefone=None, email=None):
        """
        Cadastra contato com validação prévia
        """
        # CORREÇÃO: Validação rigorosa dos parâmetros
        if not codparc:
            raise ValueError("CODPARC é obrigatório")
            
        if not nome_contato or not nome_contato.strip():
            raise ValueError("Nome do contato é obrigatório")
        
        try:
            codparc_int = int(codparc)
            if codparc_int <= 0:
                raise ValueError(f"CODPARC deve ser um número positivo: {codparc}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"CODPARC inválido: {codparc} - {e}")
        
        nome_contato_limpo = nome_contato.strip()
        
        # NOVA VALIDAÇÃO: Consulta antes de criar
        contato_existente = self.consultar_contato_por_nome_email(codparc_int, nome_contato_limpo, email)
        if contato_existente:
            print(f"[CONTATOS] Contato já existe, reutilizando: {contato_existente['CODCONTATO']} - {contato_existente['NOMECONTATO']}")
            
            # Atualiza campos se necessário
            if telefone and not contato_existente.get('TELEFONE'):
                pass  # telefone do contato existente não é atualizado (intencional)
            
            return contato_existente
        
        # Só cria se realmente não existir
        local_fields = {
            "CODPARC": {"$": str(codparc_int)},
            "NOMECONTATO": {"$": nome_contato_limpo},
        }
        
        if telefone and telefone.strip():
            local_fields["TELEFONE"] = {"$": telefone.strip()}
        if email and email.strip():
            local_fields["EMAIL"] = {"$": email.strip()}
        
        fieldset = "CODPARC,CODCONTATO,NOMECONTATO,TELEFONE,EMAIL"
        
        try:
            print(f"[CONTATOS] Criando novo contato: {nome_contato_limpo} para parceiro {codparc_int}")
            result = self.save_record("Contato", local_fields, fieldset)
            
            # CORREÇÃO: Verificar status do Sankhya
            if result.get("status") == "0":
                error_msg = result.get("statusMessage", "Erro desconhecido")
                print(f"[CONTATOS] Erro do Sankhya: {error_msg}")
                raise ValueError(f"Erro do Sankhya: {error_msg}")
            
            entities = result.get("responseBody", {}).get("entities", {})
            entity = entities.get("entity", {})
            
            contato = {
                "CODPARC": entity.get("CODPARC", {}).get("$", ""),
                "CODCONTATO": entity.get("CODCONTATO", {}).get("$", ""),
                "NOMECONTATO": entity.get("NOMECONTATO", {}).get("$", ""),
                "TELEFONE": entity.get("TELEFONE", {}).get("$", ""),
                "EMAIL": entity.get("EMAIL", {}).get("$", "")
            }
            
            print(f"[CONTATOS] Contato cadastrado: {contato['CODCONTATO']} - {contato['NOMECONTATO']}")
            return contato
            
        except Exception as e:
            print(f"[CONTATOS] Erro ao cadastrar contato: {e}")
            raise
    
    def obter_ou_criar_contato_principal(self, codparc, nome_contato, telefone=None, email=None):
        """
        Busca contato principal ou cria se não existir
        """
        if not codparc:
            print(f"[CONTATOS] CODPARC vazio para contato principal")
            return None
            
        # CORREÇÃO: Validação do CODPARC
        try:
            codparc_int = int(codparc)
            if codparc_int <= 0:
                print(f"[CONTATOS] CODPARC inválido: {codparc}")
                return None
        except (ValueError, TypeError):
            print(f"[CONTATOS] CODPARC não numérico: {codparc}")
            return None
        
        if not nome_contato or not nome_contato.strip():
            print(f"[CONTATOS] Nome do contato vazio")
            return None
        
        # Busca contatos existentes primeiro (método já corrigido)
        contatos_existentes = self.consultar_por_parceiro(codparc_int)
        
        # Se já existe contato, retorna o primeiro
        if contatos_existentes:
            contato_principal = contatos_existentes[0]
            print(f"[CONTATOS] Contato principal existente: {contato_principal['NOMECONTATO']}")
            return contato_principal
        
        # Se não existe nenhum contato, cria novo (método já corrigido)
        try:
            return self.cadastrar(codparc_int, nome_contato, telefone, email)
        except Exception as e:
            print(f"[CONTATOS] Erro ao criar contato principal: {e}")
            return None