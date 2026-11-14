"""
PedidosService CORRIGIDO - Gestão de pedidos/notas no Sankhya  
Versão: 2.5.0 - Mantém funcionalidade completa, corrige apenas problemas específicos
"""

import json
from .base import SankhyaClient
from .transportadoras import TransportadorasService
from .produtos import ProdutosService
from .estoque import EstoqueService
from config.settings import get_sankhya_defaults

class PedidosService(SankhyaClient):
    """
    Serviço para gestão de pedidos/notas no Sankhya
    CORRIGIDO: Remove referências a self.session, adiciona campos obrigatórios
    """
    
    def __init__(self, token=None):
        super().__init__(token)
        self.transportadoras_service = TransportadorasService(token)
        self.produtos_service = ProdutosService(token)
        self.estoque_service = EstoqueService(token)
    
    def obter_codlocalorig_dinamico(self, codprod):
        """
        Obtém CODLOCALORIG baseado no estoque do produto
        """
        return self.estoque_service.obter_codlocalorig_produto(codprod)
    
    def incluir(self, codparc, dtneg, itens, **kwargs):
        """
        Inclui um novo pedido no Sankhya
        ATUALIZADO: Detecta itens de estoques diferentes e cria múltiplos pedidos
        
        Args:
            codparc: Código do parceiro
            dtneg: Data de negociação (formato DD/MM/YYYY)
            itens: Lista de itens do pedido
            **kwargs: Parmetros opcionais do pedido
            
        Returns:
            dict: Resultado da operação com lista de NUNOTAs criados
        """
        try:
            print(f"[PEDIDOS] Iniciando inclusão de pedido...")
            print(f"[PEDIDOS] Parceiro: {codparc}")
            print(f"[PEDIDOS] Data: {dtneg}")
            print(f"[PEDIDOS] Itens: {len(itens)}")
    
            # Validações básicas (MANTER AS EXISTENTES)
            if not codparc:
                raise ValueError("CODPARC é obrigatório")
            if not dtneg:
                raise ValueError("DTNEG é obrigatório")
            if not itens or len(itens) == 0:
                raise ValueError("Pedido deve ter pelo menos um item. Inclusão interrompida para evitar documentos fiscais vazios.")
    
            # Formatar data se necessário (MANTER CÓDIGO EXISTENTE)
            if isinstance(dtneg, str) and '-' in dtneg:
                parts = dtneg.split('-')
                if len(parts) == 3:
                    dtneg = f"{parts[2]}/{parts[1]}/{parts[0]}"
    
  # Separar itens por estoque
            itens_por_estoque = self._separar_itens_por_estoque(itens)
            
            if len(itens_por_estoque) == 0:
                raise ValueError("Nenhum item válido para processamento")
            
  # Se há apenas um estoque, processa normalmente
            if len(itens_por_estoque) == 1:
                print(f"[PEDIDOS] ℹTodos os itens são do mesmo estoque")
                return self._incluir_pedido_unico(codparc, dtneg, itens, **kwargs)
            
  # Se há múltiplos estoques, criar múltiplos pedidos
            print(f"[PEDIDOS] Detectados {len(itens_por_estoque)} estoques diferentes")
            print(f"[PEDIDOS] Estoques: {list(itens_por_estoque.keys())}")
            print(f"[PEDIDOS] Criando pedidos separados para cada estoque...")
            
            return self._incluir_pedidos_multiplos(codparc, dtneg, itens_por_estoque, **kwargs)
            
        except Exception as e:
            erro_msg = str(e)
            print(f"[PEDIDOS] Erro ao incluir pedido: {erro_msg}")
            return {
                'sucesso': False,
                'erro': erro_msg
            }

    def _incluir_pedido_unico(self, codparc, dtneg, itens, **kwargs):
        """
        Inclui um único pedido (lógica original do método incluir)
        """
        try:
            # Obter dados do cliente para determinar CODTIPOPER
            dados_cliente = kwargs.get('dados_cliente', {})
            codlocalorig = itens[0].get('codlocalorig', '401') if itens else '401'
            
  # Determinar CODTIPOPER baseado no cliente e estoque
            codtipoper = self._determinar_codtipoper(dados_cliente, codlocalorig)
            kwargs['codtipoper'] = codtipoper
            
            # ETAPA 1: Criar cabeçalho do pedido
            print(f"[PEDIDOS] Etapa 1: Criando cabeçalho...")
            nunota = self._criar_cabecalho_pedido(codparc, dtneg, itens=itens, **kwargs)
    
            if not nunota:
                raise ValueError("Falha ao criar cabeçalho do pedido")
    
            print(f"[PEDIDOS] Cabeçalho criado: NUNOTA {nunota}")
    
            # ETAPA 2: Adicionar itens ao pedido
            
            # --- FIX INÍCIO: Restaurando lógica de adição de itens ---
            total_itens = len(itens)
            total_sucesso = 0
            itens_adicionados = []
            itens_com_erro = []
            
            print(f"[PEDIDOS] Etapa 2: Adicionando {total_itens} itens...")
            
            for i, item in enumerate(itens):
                try:
                    sequencia = self._adicionar_item_pedido(nunota, item)
                    if sequencia:
                        total_sucesso += 1
                        itens_adicionados.append(sequencia)
                    else:
                        raise Exception("Falha na API ao adicionar item (sequencia nula).")
                        
                except Exception as e:
                    print(f"[PEDIDOS] Erro ao processar item {i+1}: {str(e)}")
                    itens_com_erro.append({
                        'item_index': i, 
                        'codprod': item.get('codprod'), 
                        'erro': str(e)
                    })
            # --- FIX FIM ---
            
            # Retornar resultado
            resultado = {
                'sucesso': True,
                'nunota': nunota,
                'itens_adicionados': itens_adicionados,
                'total_itens': total_itens,
                'itens_processados': total_sucesso
            }
    
            if itens_com_erro:
                resultado['sucesso_parcial'] = True
                resultado['itens_com_erro'] = itens_com_erro
                resultado['mensagem'] = f"Pedido criado com sucesso parcial: {total_sucesso}/{total_itens} itens adicionados"
            else:
                resultado['mensagem'] = f"Pedido criado com sucesso: todos os {total_sucesso} itens foram adicionados"
    
            print(f"[PEDIDOS] Processo concluído: NUNOTA {nunota}")
        
            return resultado
    
        except Exception as e:
            erro_msg = str(e)
            print(f"[PEDIDOS] Erro ao incluir pedido único: {erro_msg}")
            return {
                'sucesso': False,
                'erro': erro_msg
            }
            
    def _separar_itens_por_estoque(self, itens):
        """
        Separa itens por estoque (401, 201, etc)
        
        Args:
            itens: Lista de itens do pedido
            
        Returns:
            dict: Dicionário com chave=estoque, valor=lista de itens
        """
        itens_por_estoque = {}
        
        for item in itens:
            codlocalorig = str(item.get('codlocalorig', '401')).strip()
            
            if codlocalorig not in itens_por_estoque:
                itens_por_estoque[codlocalorig] = []
            
            itens_por_estoque[codlocalorig].append(item)
        
        # Log detalhado
        for estoque, items in itens_por_estoque.items():
            print(f"[PEDIDOS] Estoque {estoque}: {len(items)} itens")
            for item in items:
                print(f"[PEDIDOS]   - {item.get('codprod')} (Qtd: {item.get('qtdneg')})")
        
        return itens_por_estoque
    
    def _incluir_pedidos_multiplos(self, codparc, dtneg, itens_por_estoque, **kwargs):
        """
        CORREÇÃO: Inclui múltiplos pedidos, definindo o frete específico no cabeçalho
        e garantindo que o vlr_frete_rateado (se passado em kwargs) seja honrado nos itens.
        """
        try:
            raw_woo_payload = kwargs.get('raw_woo_payload')
            if not raw_woo_payload:
                print("[PEDIDOS] Payload WooCommerce bruto ausente para mapear frete. Usando frete total/zero.")
                return self._incluir_pedido_unico(codparc, dtneg, kwargs.get('itens', []), **kwargs)
                
            # Passo: Mapear o frete por estoque
            frete_por_estoque = self._mapear_frete_por_estoque_msc(raw_woo_payload)

            resultados = []
            nunotas_criados = []
            total_itens = sum(len(items) for items in itens_por_estoque.values())
            total_itens_processados = 0
            
            # Obter dados do cliente uma vez
            dados_cliente = kwargs.get('dados_cliente', {})
            
            for estoque, itens_estoque in itens_por_estoque.items():
                print(f"\n[PEDIDOS] Processando pedido para estoque {estoque}")
                print(f"[PEDIDOS] {len(itens_estoque)} itens neste estoque")
                
                codtipoper = self._determinar_codtipoper(dados_cliente, estoque)
                kwargs_estoque = kwargs.copy()
                kwargs_estoque['codtipoper'] = codtipoper
                
                # ADIÇÃO CRÍTICA: Definir o valor de frete específico para este sub-pedido
                frete_especifico = frete_por_estoque.get(estoque, 0.0)
                kwargs_estoque['vlr_frete'] = frete_especifico # Set VLRFRETE in header
                
                # Adicionar observação
                obs_original = kwargs.get('observacoes', '')
                kwargs_estoque['observacoes'] = f"{obs_original} | Estoque: {estoque} | Frete H: R$ {frete_especifico:.2f}"
                
                # Incluir pedido para este estoque
                # Note que 'itens_estoque' já contém 'vlr_frete_rateado' se calculado em SankhyaService
                resultado_estoque = self._incluir_pedido_unico(
                    codparc, 
                    dtneg, 
                    itens_estoque, 
                    **kwargs_estoque
                )
                
                if resultado_estoque.get('sucesso'):
                    nunota = resultado_estoque['nunota']
                    nunotas_criados.append({
                        'nunota': nunota,
                        'estoque': estoque,
                        'codtipoper': codtipoper,
                        'itens_count': len(itens_estoque)
                    })
                    total_itens_processados += resultado_estoque.get('itens_processados', 0)
                    print(f"[PEDIDOS] Pedido criado para estoque {estoque}: NUNOTA {nunota} (Frete H: R$ {frete_especifico:.2f})")
                else:
                    print(f"[PEDIDOS] Erro ao criar pedido para estoque {estoque}: {resultado_estoque.get('erro')}")
                
                resultados.append({
                    'estoque': estoque,
                    'resultado': resultado_estoque
                })
            
            # Verificar se pelo menos um pedido foi criado
            if len(nunotas_criados) == 0:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum pedido foi criado com sucesso',
                    'detalhes': resultados
                }
            
            # Retorno final
            return {
                'sucesso': True,
                'multiplos_pedidos': True,
                'nunotas': nunotas_criados,
                'total_pedidos': len(nunotas_criados),
                'total_itens': total_itens,
                'itens_processados': total_itens_processados,
                'mensagem': f"Criados {len(nunotas_criados)} pedidos para {len(itens_por_estoque)} estoques diferentes",
                'detalhes': resultados
            }
            
        except Exception as e:
            erro_msg = str(e)
            print(f"[PEDIDOS] Erro ao incluir pedidos múltiplos: {erro_msg}")
            return {
                'sucesso': False,
                'erro': erro_msg
            }
    
    def _determinar_codtipoper(self, dados_cliente, codlocalorig):
        """
        Determina CODTIPOPER baseado em cliente e estoque
        
        Regras:
        - Não contribuinte + 401 = 304
        - Não contribuinte + 201 = 308
        - Contribuinte + 401 = 329
        - Contribuinte + 201 = 330
        """
        is_contribuinte = self._verificar_cliente_contribuinte(dados_cliente)
        estoque = str(codlocalorig).strip()
        
        print(f"[PEDIDOS] Determinando CODTIPOPER:")
        print(f"[PEDIDOS]   Contribuinte: {'SIM' if is_contribuinte else 'NÃO'}")
        print(f"[PEDIDOS]   Estoque: {estoque}")
        
        if not is_contribuinte:
            if estoque == '401':
                codtipoper = '304'
            elif estoque == '201':
                codtipoper = '308'
            else:
                codtipoper = '304'
                print(f"[PEDIDOS] Estoque {estoque} não mapeado, usando padrão: {codtipoper}")
        else:
            if estoque == '401':
                codtipoper = '329'
            elif estoque == '201':
                codtipoper = '330'
            else:
                codtipoper = '329'
                print(f"[PEDIDOS] Estoque {estoque} não mapeado, usando padrão: {codtipoper}")
        
        print(f"[PEDIDOS] CODTIPOPER determinado: {codtipoper}")
        return codtipoper
    
    def _verificar_cliente_contribuinte(self, dados_cliente):
        """
        Verifica se cliente possui Inscrição Estadual
        """
        if not dados_cliente:
            print(f"[PEDIDOS] Dados do cliente não fornecidos")
            return False
        
        # Extrair billing
        billing = dados_cliente.get('billing', {}) if 'billing' in dados_cliente else dados_cliente
        
        # 1. Buscar em campos diretos do billing
        ie_fields = ['ie', 'rg_ie', 'inscricao_estadual', 'state_registration']
        for field in ie_fields:
            ie_value = billing.get(field, '').strip()
            if ie_value and ie_value.upper() not in ['', 'ISENTO', 'ISENTA']:
                print(f"[PEDIDOS] Inscrição Estadual encontrada em billing.{field}: {ie_value}")
                return True
        
        # 2. Buscar em meta_data
        meta_data = dados_cliente.get('meta_data', [])
        ie_meta_keys = [
            'billing_ie', '_billing_ie', 
            'billing_rg_ie', '_billing_rg_ie',
            'billing_inscricao_estadual', '_billing_inscricao_estadual'
        ]
        
        for meta in meta_data:
            key = meta.get('key', '')
            if key in ie_meta_keys:
                value = str(meta.get('value', '')).strip()
                if value and value.upper() not in ['', 'ISENTO', 'ISENTA']:
                    print(f"[PEDIDOS] Inscrição Estadual encontrada em meta_data.{key}: {value}")
                    return True
        
        print(f"[PEDIDOS] ℹCliente sem inscrição estadual (não contribuinte)")
        return False    
        
    def _criar_cabecalho_pedido(self, codparc, dtneg, **kwargs):
        """
        ETAPA 1: Cria apenas o cabeçalho do pedido
        Conforme documentação Sankhya, primeiro criamos o pedido sem itens
        """
        try:
            url = self.get_commerce_url("CACSP.incluirNota")

            # Obter configurações padrão
            config_defaults = get_sankhya_defaults()

            # Definir a variável cabecalho (CORRIGIDO: Movido para antes da primeira utilização)
            cabecalho = {
                "NUNOTA": {},  # Vazio para o Sankhya gerar automaticamente
                "CODPARC": {"$": str(codparc)},
                "DTNEG": {"$": dtneg},
                "CODTIPOPER": {"$": str(kwargs.get('codtipoper', config_defaults.get('CODTIPOPER', '2100')))},
                "CODTIPVENDA": {"$": str(kwargs.get('codtipvenda', config_defaults.get('CODTIPVENDA', '10')))},
                "CODNAT": {"$": str(kwargs.get('codnat', config_defaults.get('CODNAT', '10')))},
                "CODVEND": {"$": str(kwargs.get('codvend', config_defaults.get('CODVEND', '0')))},
                "CODEMP": {"$": str(kwargs.get('codemp', config_defaults.get('CODEMP', '1')))},
                "TIPMOV": {"$": "P"}  # P = Pedido de venda
            }

  # Mapear ID do WooCommerce para campo customizado
            if kwargs.get('id_woo'):
                # Garante que o campo AD_IDWOOCOMMERCE foi criado na tabela TGFCAB
                cabecalho["AD_IDWOOCOMMERCE"] = {"$": str(kwargs['id_woo'])}
                print(f"[PEDIDOS] AD_IDWOOCOMMERCE: {kwargs['id_woo']}")            

            # Adicionar campos opcionais se fornecidos
            if kwargs.get('observacoes'):
                cabecalho["OBSERVACAO"] = {"$": kwargs['observacoes']}

            # CAMPOS DA TRANSPORTADORA
            if kwargs.get('codparctransp'):
                cabecalho["CODPARCTRANSP"] = {"$": str(kwargs['codparctransp'])}
                print(f"[PEDIDOS] CODPARCTRANSP: {kwargs['codparctransp']}")

            # CORREÇÃO DO VLRFRETE + TIPFRETE
            if kwargs.get('vlr_frete') is not None:
                vlr_frete_valor = kwargs['vlr_frete']

                try:
                    vlr_frete_float = float(vlr_frete_valor)
                    if vlr_frete_float > 0:
                        # IMPORTANTE: Enviar valor como STRING formatada
                        cabecalho["VLRFRETE"] = {"$": str(vlr_frete_float)}  # Converter para string
                        cabecalho["TIPFRETE"] = {"$": "S"}  # S = Incluso no preço
                        cabecalho["CIF_FOB"] = {"$": "C"}   # C = CIF (frete por conta do vendedor)

                        # Adicionar também no VLRFRETETOTAL se o campo existir
                        cabecalho["VLRFRETETOTAL"] = {"$": str(vlr_frete_float)}

                        print(f"[PEDIDOS] Valor Frete: R$ {vlr_frete_float:.2f}")
                        print(f"[PEDIDOS] TIPFRETE: S (Incluso)")
                        print(f"[PEDIDOS] CIF_FOB: C (CIF)")
                    else:
                        # Frete zerado
                        cabecalho["VLRFRETE"] = {"$": "0"}
                        cabecalho["TIPFRETE"] = {"$": "S"}
                        cabecalho["CIF_FOB"] = {"$": "S"}  # S = Sem Frete quando valor é zero
                        print(f"[PEDIDOS] Valor frete zerado")
                except (ValueError, TypeError) as e:
                    print(f"[PEDIDOS] Erro ao converter valor frete: {vlr_frete_valor} - {e}")
                    cabecalho["TIPFRETE"] = {"$": "S"}
                    cabecalho["CIF_FOB"] = {"$": "S"}
            else:
                # Sem frete informado
                cabecalho["TIPFRETE"] = {"$": "S"}
                cabecalho["CIF_FOB"] = {"$": "S"}  # S = Sem Frete
                print(f"[PEDIDOS] Sem frete informado, TIPFRETE = S")
            # OUTROS CAMPOS IMPORTANTES
            # Natureza da operação (se fornecida)
            if kwargs.get('codnat'):
                cabecalho["CODNAT"] = {"$": str(kwargs['codnat'])}

            # Centro de resultado (se fornecido)
            if kwargs.get('codcencus'):
                cabecalho["CODCENCUS"] = {"$": str(kwargs['codcencus'])}

            # Projeto (se fornecido)
            if kwargs.get('codproj'):
                cabecalho["CODPROJ"] = {"$": str(kwargs['codproj'])}

            # Observações sobre o frete (se houver)
            if kwargs.get('obs_frete'):
                obs_completa = kwargs.get('observacoes', '')
                obs_completa += f"\nFrete: {kwargs['obs_frete']}"
                cabecalho["OBSERVACAO"] = {"$": obs_completa}

            # Data de entrega prevista (se fornecida)
            if kwargs.get('dtentrega'):
                cabecalho["DTENTREGA"] = {"$": kwargs['dtentrega']}

            # Código do contato (se fornecido)
            if kwargs.get('codcontato'):
                cabecalho["CODCONTATO"] = {"$": str(kwargs['codcontato'])}

            print(f"[PEDIDOS] Criando cabeçalho do pedido...")
            print(f"[PEDIDOS] CODPARC: {codparc}")
            print(f"[PEDIDOS] DTNEG: {dtneg}")
            print(f"[PEDIDOS] CODTIPOPER: {cabecalho['CODTIPOPER']['$']}")

            # DEBUG: Log do payload completo
            print(f"[DEBUG PEDIDOS] VLRFRETE: {cabecalho.get('VLRFRETE', 'NÃO DEFINIDO')}")
            print(f"[DEBUG PEDIDOS] TIPFRETE: {cabecalho.get('TIPFRETE', 'NÃO DEFINIDO')}")
            print(f"[DEBUG PEDIDOS] CIF_FOB: {cabecalho.get('CIF_FOB', 'NÃO DEFINIDO')}")

            # Montar payload sem itens (primeira etapa)
            payload = {
                "serviceName": "CACSP.incluirNota",
                "requestBody": {
                    "nota": {
                        "cabecalho": cabecalho
                        # SEM seção "itens" - será adicionado depois
                    }
                }
            }

            # DEBUG: Log do JSON que será enviado
            import json
            print(f"[DEBUG PEDIDOS] JSON enviado:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))

            # Fazer requisição
            resultado = self.post_request(url, payload)

            # DEBUG: Log da resposta do Sankhya
            print(f"[DEBUG PEDIDOS] Resposta do Sankhya:")
            print(json.dumps(resultado, indent=2, ensure_ascii=False))

            # Verificar resultado
            if resultado.get("status") == "1":
                nunota = resultado.get("responseBody", {}).get("pk", {}).get("NUNOTA", {}).get("$")
                print(f"[PEDIDOS] Cabeçalho criado - NUNOTA: {nunota}")
                return nunota
            else:
                error_msg = resultado.get("statusMessage", "Erro desconhecido")
                print(f"[PEDIDOS] Erro ao criar cabeçalho: {error_msg}")

                # DEBUG: Verificar se há mensagens específicas sobre VLRFRETE
                if "frete" in error_msg.lower() or "vlrfrete" in error_msg.lower():
                    print(f"[PEDIDOS] ERRO RELACIONADO AO FRETE: {error_msg}")

                raise Exception(f"Erro ao criar cabeçalho do pedido: {error_msg}")

        except Exception as e:
            print(f"[PEDIDOS] Erro no _criar_cabecalho_pedido: {e}")
            raise

    def atualizar_frete_sem_recalculo(self, nunota, vlr_frete, codparctransp=None):
        """
        CORRIGIDO: Atualiza o frete usando estrutura correta do DatasetSP.save
        SEM definir ICMS como zero - deixa o Sankhya calcular automaticamente
        """
        try:
            url = self.get_url("DatasetSP.save")

            # Estrutura correta conforme documentação Sankhya
            # SEM incluir ICMSFRETE e BASEICMSFRETE - deixa o Sankhya calcular
            fields = ["NUNOTA", "VLRFRETE", "TIPFRETE", "CIF_FOB"]
            values = {
                "0": str(nunota),
                "1": str(float(vlr_frete)),
                "2": "S",  # S = Incluso
                "3": "C"   # C = CIF
            }

            # Adicionar transportadora se informada
            if codparctransp:
                fields.append("CODPARCTRANSP")
                values[str(len(fields)-1)] = str(codparctransp)

            payload = {
                "serviceName": "DatasetSP.save",
                "requestBody": {
                    "entityName": "CabecalhoNota",  # Nome correto da entidade TGFCAB
                    "standAlone": False,
                    "fields": fields,
                    "records": [
                        {
                            "pk": {
                                "NUNOTA": str(nunota)
                            },
                            "values": values
                        }
                    ]
                }
            }

            print(f"[PEDIDOS] Atualizando frete via DatasetSP.save (sem ICMS fixo)...")

            # Debug do payload
            import json
            print(f"[DEBUG FRETE] Payload enviado:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))

            resultado = self.post_request(url, payload)

            print(f"[DEBUG FRETE] Resposta do Sankhya:")
            print(json.dumps(resultado, indent=2, ensure_ascii=False))

            if resultado.get("status") == "1":
                print(f"[PEDIDOS] Frete atualizado: R$ {vlr_frete} (ICMS será calculado automaticamente)")
                return True
            else:
                error_msg = resultado.get("statusMessage", "Erro desconhecido")
                print(f"[PEDIDOS] Erro ao atualizar frete: {error_msg}")
                return False

        except Exception as e:
            print(f"[PEDIDOS] Erro ao atualizar frete: {e}")
            return False

    def _recalculo_alternativo(self, nunota):
        """
        Método alternativo para forçar recálculo
        """
        try:
            url = self.get_url("DatasetSP.save")

            payload = {
                "serviceName": "DatasetSP.save",
                "requestBody": {
                    "dataSet": {
                        "rootEntity": "Cabecalho",
                        "includePresentationFields": "N",
                        "dataRow": {
                            "localFields": {
                                "RECALCTOTAIS": {
                                    "$": "S"
                                }
                            },
                            "key": {
                                "NUNOTA": {
                                    "$": str(nunota)
                                }
                            }
                        }
                    }
                }
            }

            resultado = self.post_request(url, payload)
            return resultado.get("status") == "1"

        except Exception as e:
            print(f"[PEDIDOS] Erro no recálculo alternativo: {e}")
            return False
      
    def _adicionar_item_pedido(self, nunota, item):
        """
        ETAPA 2: Adiciona um item ao pedido existente
        Conforme documentação oficial da API Sankhya
        MODIFICADO: Adiciona AD_VLRFRETEECOMMERCE quando fornecido
        """
        try:
            url = self.get_commerce_url("CACSP.incluirAlterarItemNota")

            # Obter CODLOCALORIG dinamicamente se não fornecido
            codlocalorig = item.get('codlocalorig')
            if not codlocalorig:
                codlocalorig = self.obter_codlocalorig_dinamico(item['codprod'])
                if not codlocalorig:
                    codlocalorig = "0"  # Fallback padrão

            # Preparar dados do item conforme documentação oficial
            qtdneg = float(item.get('qtdneg', 1))
            vlrunit = float(item.get('vlrunit', 0))
            vlrtot = qtdneg * vlrunit

            # Calcular desconto se fornecido
            percdesc = float(item.get('percdesc', 0))
            vlrdesc = 0
            if percdesc > 0:
                vlrdesc = vlrtot * (percdesc / 100)
                vlrtot = vlrtot - vlrdesc  # Ajustar valor total com desconto

            item_data = {
                "CODPROD": {"$": str(item['codprod'])},
                "NUNOTA": {"$": str(nunota)},
                "SEQUENCIA": {"$": ""},  # String vazia para auto-incrementar
                "QTDNEG": {"$": str(qtdneg)},
                "VLRUNIT": {"$": str(vlrunit)},
                "VLRTOT": {"$": str(vlrtot)},
                "CODVOL": {"$": item.get('codvol', 'UN')},
                "VLRDESC": {"$": str(vlrdesc)},
                "PERCDESC": {"$": str(percdesc)}
            }

            # Adicionar CODLOCALORIG apenas se disponível e válido
            if codlocalorig and codlocalorig != "0":
                item_data["CODLOCALORIG"] = {"$": str(codlocalorig)}

            # NOVA FUNCIONALIDADE: Adicionar frete rateado se fornecido
            if item.get('vlr_frete_rateado') is not None and float(item.get('vlr_frete_rateado', 0)) > 0:
                item_data["AD_VLRFRETEECOMMERCE"] = {"$": str(item['vlr_frete_rateado'])}
                print(f"[PEDIDOS]   - FRETE RATEADO: R$ {item['vlr_frete_rateado']:.2f}")

            print(f"[PEDIDOS] Adicionando item ao pedido {nunota}...")
            print(f"[PEDIDOS]   - CODPROD: {item['codprod']}")
            print(f"[PEDIDOS]   - QTDNEG: {qtdneg}")
            print(f"[PEDIDOS]   - VLRUNIT: R$ {vlrunit:.2f}")
            print(f"[PEDIDOS]   - VLRTOT: R$ {vlrtot:.2f}")
            print(f"[PEDIDOS]   - CODLOCALORIG: {codlocalorig}")

            # Estrutura do payload conforme documentação
            payload = {
                "serviceName": "CACSP.incluirAlterarItemNota",
                "requestBody": {
                    "nota": {
                        "NUNOTA": str(nunota),
                        "itens": {
                            "item": item_data
                        }
                    }
                }
            }

            # Debug do payload
            import json
            print(f"[DEBUG PEDIDOS] Payload do item:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))

            # Fazer requisição
            resultado = self.post_request(url, payload)

            # Verificar resultado
            if resultado.get("status") == "1":
                # Extrair sequência do item adicionado
                response_body = resultado.get("responseBody", {})
                pk = response_body.get("pk", {})
                sequencia = pk.get("SEQUENCIA", {}).get("$", "0")

                print(f"[PEDIDOS] Item adicionado - Sequência: {sequencia}")
                if item.get('vlr_frete_rateado'):
                    print(f"[PEDIDOS] Frete rateado incluído: R$ {item['vlr_frete_rateado']:.2f}")
                return sequencia
            else:
                error_msg = resultado.get("statusMessage", "Erro desconhecido")
                print(f"[PEDIDOS] Erro ao adicionar item: {error_msg}")

                # Debug adicional para entender o erro
                if "responseBody" in resultado:
                    print(f"[DEBUG PEDIDOS] Response body: {resultado.get('responseBody')}")

                raise Exception(f"Erro ao adicionar item: {error_msg}")

        except Exception as e:
            print(f"[PEDIDOS] Erro no _adicionar_item_pedido: {e}")
            # Não propaga o erro para tentar adicionar outros itens
            return None
      
    def calcular_rateio_frete_cubagem(self, line_items, vlr_frete_total):
        """
        CORRIGIDO: Vincula dimensões existentes no WooCommerce
        """
        try:
            print(f"[PEDIDOS] Calculando rateio de frete por cubagem...")
            print(f"[PEDIDOS] Frete total: R$ {vlr_frete_total:.2f}")
    
            itens_com_cubagem = []
            cubagem_total = 0
    
            for item in line_items:
                product_id = item.get('product_id', 0)
                sku = item.get('sku', '')
                qtd = float(item.get('quantity', 1))
    
                print(f"[PEDIDOS] Analisando item {sku} (ID: {product_id})")
    
                # CORREÇÃO 1: Buscar dimensões em múltiplas fontes
                altura = self._obter_dimensao_item(item, 'height')
                largura = self._obter_dimensao_item(item, 'width')
                comprimento = self._obter_dimensao_item(item, 'length')
    
                print(f"[PEDIDOS] Dimensões extraídas:")
                print(f"[PEDIDOS]   Altura: {altura:.3f}m")
                print(f"[PEDIDOS]   Largura: {largura:.3f}m")
                print(f"[PEDIDOS]   Comprimento: {comprimento:.3f}m")
    
                # Calcular cubagem do item (m³)
                cubagem_unitaria = altura * largura * comprimento
                cubagem_item = cubagem_unitaria * qtd
                cubagem_total += cubagem_item
    
                itens_com_cubagem.append({
                    'product_id': product_id,
                    'sku': sku,
                    'qtd': qtd,
                    'cubagem': cubagem_item,
                    'cubagem_unitaria': cubagem_unitaria,
                    'altura': altura,
                    'largura': largura,
                    'comprimento': comprimento
                })
    
                print(f"[PEDIDOS] Item {sku}: {cubagem_unitaria:.6f} m³/un x {qtd} = {cubagem_item:.6f} m³")
    
            print(f"[PEDIDOS] Cubagem total: {cubagem_total:.6f} m³")
    
            # Se ainda estiver muito pequeno, fazer rateio igual
            if cubagem_total < 0.000001:
                print(f"[PEDIDOS] Usando rateio igual por quantidade")
                qtd_total = sum(float(item.get('quantity', 1)) for item in line_items)
    
                for item in itens_com_cubagem:
                    percentual = (item['qtd'] / qtd_total * 100) if qtd_total > 0 else (100 / len(itens_com_cubagem))
                    item['vlr_frete_rateado'] = round(vlr_frete_total * item['qtd'] / qtd_total, 2) if qtd_total > 0 else 0
                    item['percentual'] = percentual
            else:
                # Ratear frete proporcional à cubagem
                for item in itens_com_cubagem:
                    percentual = item['cubagem'] / cubagem_total
                    item['vlr_frete_rateado'] = round(vlr_frete_total * percentual, 2)
                    item['percentual'] = percentual * 100
    
                    print(f"[PEDIDOS] Item {item['sku']}: {item['percentual']:.2f}% = R$ {item['vlr_frete_rateado']:.2f}")
    
            # Ajustar diferença de arredondamento no último item
            soma_rateio = sum(item['vlr_frete_rateado'] for item in itens_com_cubagem)
            if abs(soma_rateio - vlr_frete_total) > 0.01 and itens_com_cubagem:
                diferenca = vlr_frete_total - soma_rateio
                itens_com_cubagem[-1]['vlr_frete_rateado'] += diferenca
                print(f"[PEDIDOS] Ajuste de arredondamento: R$ {diferenca:.2f}")
    
            return itens_com_cubagem
    
        except Exception as e:
            print(f"[PEDIDOS] Erro ao calcular rateio: {e}")
            return None
    
    def _obter_dimensao_item(self, item, dimensao):
        """
        Extrai dimensão específica de múltiplas fontes
        """
        # Valor padrão em metros
        padrao = 0.1  # 10cm
        
        # 1. Buscar em meta_data (prioridade alta)
        meta_data = item.get('meta_data', [])
        for meta in meta_data:
            key = meta.get('key', '').lower()
            value = meta.get('value', '')
            
            # Mapear chaves para dimensões
            chaves_height = ['_height', 'height', 'altura', 'h']
            chaves_width = ['_width', 'width', 'largura', 'w']
            chaves_length = ['_length', 'length', 'comprimento', 'l', 'depth']
            
            if dimensao == 'height' and any(chave in key for chave in chaves_height):
                return self._converter_para_metros(value)
            elif dimensao == 'width' and any(chave in key for chave in chaves_width):
                return self._converter_para_metros(value)
            elif dimensao == 'length' and any(chave in key for chave in chaves_length):
                return self._converter_para_metros(value)
        
        # 2. Buscar em campos diretos do item
        if dimensao in item:
            return self._converter_para_metros(item[dimensao])
        
        # 3. Buscar em objeto dimensions
        dimensions = item.get('dimensions', {})
        if isinstance(dimensions, dict) and dimensao in dimensions:
            return self._converter_para_metros(dimensions[dimensao])
        
        # 4. Buscar em campos alternativos
        campos_alt = {
            'height': ['altura', 'h'],
            'width': ['largura', 'w'], 
            'length': ['comprimento', 'l', 'depth']
        }
        
        for campo_alt in campos_alt.get(dimensao, []):
            if campo_alt in item:
                return self._converter_para_metros(item[campo_alt])
        
        print(f"[PEDIDOS] Dimensão {dimensao} não encontrada, usando padrão: {padrao:.3f}m")
        return padrao
    
    def _converter_para_metros(self, valor):
        """
        Converte valor para metros detectando unidade
        """
        try:
            val = float(valor) if valor else 0
            if val <= 0:
                return 0.1  # 10cm padrão
            
            # Detectar unidade pelo valor
            if val > 1000:
                # Provavelmente mm
                return val / 1000
            elif val > 10:
                # Provavelmente cm  
                return val / 100
            else:
                # Já em metros ou muito pequeno
                return max(val, 0.01)  # Mínimo 1cm
        except (ValueError, TypeError):
            return 0.1  # 10cm padrão

    def aplicar_frete_rateado_nos_itens(self, nunota, itens_com_frete):
        """
        Aplica o frete rateado no campo AD_VLRFRETEECOMMERCE de cada item
        """
        try:
            print(f"[PEDIDOS] Aplicando frete rateado nos itens da nota {nunota}...")

            # Buscar sequências dos itens na nota
            itens_nota = self.load_records(
                entity="ItemNota",
                fields="NUNOTA,SEQUENCIA,CODPROD",
                criteria={
                    "expression": {"$": "this.NUNOTA = ?"},
                    "parameter": [{"type": "I", "value": str(nunota)}]
                }
            )

            entities = itens_nota.get('responseBody', {}).get('entities', {})
            items = entities.get('entity', [])
            if not isinstance(items, list):
                items = [items]

            # Mapear por SKU/CODPROD
            mapa_sequencias = {}
            for item in items:
                codprod = self._extract_value(item.get('f2'))  # CODPROD
                sequencia = self._extract_value(item.get('f1'))  # SEQUENCIA
                mapa_sequencias[codprod] = sequencia

            # Atualizar cada item com seu frete rateado
            sucesso_total = True
            for item_frete in itens_com_frete:
                sku = item_frete.get('sku', '')
                vlr_frete = item_frete.get('vlr_frete_rateado', 0)

                # Encontrar sequência correspondente
                sequencia = mapa_sequencias.get(sku)
                if not sequencia:
                    print(f"[PEDIDOS] Sequência não encontrada para SKU {sku}")
                    continue

                # Atualizar campo AD_VLRFRETEECOMMERCE
                try:
                    url = self.get_base_url("mge/service.sbr?serviceName=CRUDServiceProvider.saveRecord")

                    payload = {
                        "serviceName": "CRUDServiceProvider.saveRecord",
                        "requestBody": {
                            "dataSet": {
                                "rootEntity": "ItemNota",
                                "includePresentationFields": "N",
                                "dataRow": {
                                    "localFields": {
                                        "NUNOTA": {"$": str(nunota)},
                                        "SEQUENCIA": {"$": str(sequencia)},
                                        "AD_VLRFRETEECOMMERCE": {"$": str(vlr_frete)}
                                    }
                                },
                                "entity": {
                                    "fieldset": {
                                        "list": "NUNOTA,SEQUENCIA,AD_VLRFRETEECOMMERCE"
                                    }
                                }
                            }
                        }
                    }

                    resultado = self.post_request(url, payload)

                    if resultado.get("status") == "1":
                        print(f"[PEDIDOS] Item {sequencia} - SKU {sku}: Frete R$ {vlr_frete:.2f} aplicado")
                    else:
                        print(f"[PEDIDOS] Erro ao atualizar item {sequencia}: {resultado.get('statusMessage')}")
                        sucesso_total = False

                except Exception as e:
                    print(f"[PEDIDOS] Erro ao atualizar item {sequencia}: {e}")
                    sucesso_total = False

            return sucesso_total

        except Exception as e:
            print(f"[PEDIDOS] Erro ao aplicar frete nos itens: {e}")
            return False

      
    def consultar(self, nunota):
        """
        Consulta pedido por NUNOTA
        """
        try:
            criteria = {
                "expression": {
                    "$": "this.NUNOTA = ?"
                },
                "parameter": [
                    {
                        "type": "I",
                        "value": str(nunota)
                    }
                ]
            }
            
            resultado = self.load_records(
                entity="CabecalhoNota",
                fields="NUNOTA,CODPARC,DTNEG,VLRNOTA,STATUSNOTA",
                criteria=criteria
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            if int(entities.get("total", "0")) > 0:
                entity = entities.get("entity")
                if isinstance(entity, list):
                    entity = entity[0]
                
                return {
                    'encontrado': True,
                    'nunota': self._extract_value(entity.get('f0')),
                    'codparc': self._extract_value(entity.get('f1')),
                    'dtneg': self._extract_value(entity.get('f2')),
                    'vlrnota': self._extract_value(entity.get('f3')),
                    'status': self._extract_value(entity.get('f4'))
                }
            
            return {'encontrado': False}
            
        except Exception as e:
            print(f"[PEDIDOS] Erro na consulta: {e}")
            return {'encontrado': False, 'erro': str(e)}
    
    def listar_por_parceiro(self, codparc, limite=10):
        """
        Lista pedidos de um parceiro
        """
        try:
            criteria = {
                "expression": {
                    "$": "this.CODPARC = ? AND this.TIPMOV = ?"
                },
                "parameter": [
                    {"type": "I", "value": str(codparc)},
                    {"type": "S", "value": "P"}  # P = Pedido de venda
                ]
            }
            
            resultado = self.load_records(
                entity="CabecalhoNota",
                fields="NUNOTA,DTNEG,VLRNOTA,STATUSNOTA",
                criteria=criteria,
                limit=limite
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                pedidos = []
                for entity in entity_list:
                    pedido = {
                        'nunota': self._extract_value(entity.get('f0')),
                        'dtneg': self._extract_value(entity.get('f1')),
                        'vlrnota': self._extract_value(entity.get('f2')),
                        'status': self._extract_value(entity.get('f3'))
                    }
                    pedidos.append(pedido)
                
                return {
                    'total': total,
                    'pedidos': pedidos
                }
            
            return {'total': 0, 'pedidos': []}
            
        except Exception as e:
            print(f"[PEDIDOS] Erro ao listar pedidos: {e}")
            return {'total': 0, 'pedidos': [], 'erro': str(e)}
    
    def atualizar_status(self, nunota, novo_status):
        """
        Atualiza status de um pedido
        """
        try:
            dados_atualizacao = {
                "NUNOTA": {"$": str(nunota)},
                "STATUSNOTA": {"$": str(novo_status)}
            }
            
            payload = {
                "serviceName": "DatasetSP.save",
                "requestBody": {
                    "dataSet": {
                        "rootEntity": "CabecalhoNota",
                        "includePresentationFields": "S",
                        "entity": {
                            "fieldset": {
                                "list": "NUNOTA,STATUSNOTA"
                            }
                        },
                        "rows": [dados_atualizacao]
                    }
                }
            }
            
            print(f"[PEDIDOS] Atualizando status do pedido {nunota} para '{novo_status}'")
            
            url = self.get_url("DatasetSP.save")
            resultado = self.post_request(url, payload)
            
            if resultado.get("status") == "1":
                print(f"[PEDIDOS] Status atualizado com sucesso")
                return {
                    'sucesso': True,
                    'nunota': nunota,
                    'novo_status': novo_status,
                    'dados_resposta': resultado
                }
            else:
                erro_msg = resultado.get("statusMessage", "Erro desconhecido")
                print(f"[PEDIDOS] Erro na atualização: {erro_msg}")
                
                return {
                    'sucesso': False,
                    'erro': erro_msg,
                    'dados_resposta': resultado
                }
                
        except Exception as e:
            print(f"[PEDIDOS] Erro na atualização do status: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def cancelar(self, nunota, motivo=None):
        """
        Cancela um pedido
        """
        try:
            observacao_cancelamento = f"Pedido cancelado via integração WooCommerce"
            if motivo:
                observacao_cancelamento += f" - Motivo: {motivo}"
            
            dados_cancelamento = {
                "NUNOTA": {"$": str(nunota)},
                "STATUSNOTA": {"$": "C"},  # C = Cancelado
                "OBSERVACAO": {"$": observacao_cancelamento[:500]}
            }
            
            payload = {
                "serviceName": "DatasetSP.save", 
                "requestBody": {
                    "dataSet": {
                        "rootEntity": "CabecalhoNota",
                        "includePresentationFields": "S",
                        "entity": {
                            "fieldset": {
                                "list": "NUNOTA,STATUSNOTA,OBSERVACAO"
                            }
                        },
                        "rows": [dados_cancelamento]
                    }
                }
            }
            
            print(f"[PEDIDOS] Cancelando pedido {nunota}")
            if motivo:
                print(f"[PEDIDOS] Motivo: {motivo}")
            
            url = self.get_url("DatasetSP.save")
            resultado = self.post_request(url, payload)
            
            if resultado.get("status") == "1":
                print(f"[PEDIDOS] Pedido cancelado com sucesso")
                return {
                    'sucesso': True,
                    'nunota': nunota,
                    'status': 'cancelado',
                    'motivo': motivo,
                    'dados_resposta': resultado
                }
            else:
                erro_msg = resultado.get("statusMessage", "Erro desconhecido")
                print(f"[PEDIDOS] Erro no cancelamento: {erro_msg}")
                
                return {
                    'sucesso': False,
                    'erro': erro_msg,
                    'dados_resposta': resultado
                }
                
        except Exception as e:
            print(f"[PEDIDOS] Erro no cancelamento: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def diagnosticar_pedido(self, produtos_wc):
        """
        Diagnóstica se produtos do WooCommerce podem ser processados
        """
        try:
            total_itens = len(produtos_wc)
            mapa_itens = {}
            itens_validos = 0
            itens_problematicos = 0
            problemas = []
            
            print(f"[PEDIDOS] Diagnosticando {total_itens} produtos...")
            
            for i, item in enumerate(produtos_wc):
                item_id = str(item.get('id', ''))
                product_id = item.get('product_id', 0)
                name = item.get('name', 'Produto sem nome')
                quantity = item.get('quantity', 1)
                
                print(f"[PEDIDOS] Item {i+1}/{total_itens}: {name} (ID: {item_id})")
                
                # Validações básicas
                if not item_id or item_id == '0':
                    problema = f"Item {i+1}: ID inválido"
                    problemas.append(problema)
                    mapa_itens[item_id] = {
                        'pode_processar': False,
                        'erro': 'ID inválido'
                    }
                    itens_problematicos += 1
                    print(f"[PEDIDOS] {problema}")
                    continue
                
                if not product_id or product_id <= 0:
                    problema = f"Item {item_id}: Product ID inválido ({product_id})"
                    problemas.append(problema)
                    mapa_itens[item_id] = {
                        'pode_processar': False,
                        'erro': 'Product ID inválido'
                    }
                    itens_problematicos += 1
                    print(f"[PEDIDOS] {problema}")
                    continue
                
                if quantity <= 0:
                    problema = f"Item {item_id}: Quantidade inválida ({quantity})"
                    problemas.append(problema)
                    mapa_itens[item_id] = {
                        'pode_processar': False,
                        'erro': 'Quantidade inválida'
                    }
                    itens_problematicos += 1
                    print(f"[PEDIDOS] {problema}")
                    continue
                
                # Tenta mapear o produto no Sankhya
                try:
                    produto_mapeado = self.produtos_service.mapear_produto(item)

                    if produto_mapeado and produto_mapeado.get('produto_encontrado', False):
                        # Obtém CODLOCALORIG dinmico
                        codlocalorig = self.obter_codlocalorig_dinamico(produto_mapeado['codprod_sankhya'])
                        if not codlocalorig:
                            codlocalorig = '401'  # Padrão

                        mapa_itens[item_id] = {
                            'pode_processar': True,
                            'codprod': produto_mapeado['codprod_sankhya'],
                            'codlocalorig': codlocalorig,
                            'codvol': produto_mapeado.get('codvol', 'UN'),
                            'nome_produto': produto_mapeado.get('descricao_sankhya', name)
                        }
                        itens_validos += 1
                        print(f"[PEDIDOS] Item {item_id} válido: {produto_mapeado['codprod_sankhya']}")
                    else:
                        # Produto não encontrado no Sankhya
                        problema = f"Item {item_id}: Produto não encontrado no Sankhya"
                        problemas.append(problema)
                        mapa_itens[item_id] = {
                            'pode_processar': False,
                            'erro': 'Produto não encontrado no Sankhya'
                        }
                        itens_problematicos += 1
                        print(f"[PEDIDOS] {problema}")
        
                except Exception as e:
                    problema = f"Item {item_id}: Erro no mapeamento - {str(e)}"
                    problemas.append(problema)
                    mapa_itens[item_id] = {
                        'pode_processar': False,
                        'erro': f'Erro no mapeamento: {str(e)}'
                    }
                    itens_problematicos += 1
                    print(f"[PEDIDOS] {problema}")
            
            # Determina se pode processar o pedido
            pode_processar = itens_validos > 0 and itens_problematicos == 0
            
            print(f"[PEDIDOS] RESULTADO DIAGNÓSTICO:")
            print(f"[PEDIDOS]   Total de itens: {total_itens}")
            print(f"[PEDIDOS]   Itens válidos: {itens_validos}")
            print(f"[PEDIDOS]   Itens problemáticos: {itens_problematicos}")
            print(f"[PEDIDOS]   Pode processar: {'SIM' if pode_processar else 'NÃO'}")
            
            if problemas:
                print(f"[PEDIDOS] Problemas encontrados:")
                for problema in problemas:
                    print(f"[PEDIDOS]     - {problema}")
            
            return {
                'pode_processar': pode_processar,
                'total_itens': total_itens,
                'itens_validos': itens_validos,
                'itens_problematicos': itens_problematicos,
                'problemas': problemas,
                'mapa_itens': mapa_itens
            }
            
        except Exception as e:
            print(f"[PEDIDOS] Erro no diagnóstico: {e}")
            return {
                'pode_processar': False,
                'total_itens': 0,
                'itens_validos': 0,
                'itens_problematicos': 0,
                'problemas': [f"Erro no diagnóstico: {str(e)}"],
                'mapa_itens': {}
            }
    
    def listar_todos(self, limite=50, filtros=None):
        """
        Lista todos os pedidos com filtros opcionais
        """
        try:
            # Monta critérios de busca
            expression_parts = ["this.TIPMOV = ?"]
            parameters = [{"type": "S", "value": "P"}]  # P = Pedido de venda
            
            if filtros:
                if filtros.get('status'):
                    expression_parts.append("this.STATUSNOTA = ?")
                    parameters.append({"type": "S", "value": filtros['status']})
                
                if filtros.get('data_inicio'):
                    expression_parts.append("this.DTNEG >= ?")
                    parameters.append({"type": "D", "value": filtros['data_inicio']})
                
                if filtros.get('data_fim'):
                    expression_parts.append("this.DTNEG <= ?")
                    parameters.append({"type": "D", "value": filtros['data_fim']})
                
                if filtros.get('codparc'):
                    expression_parts.append("this.CODPARC = ?")
                    parameters.append({"type": "I", "value": str(filtros['codparc'])})
            
            criteria = {
                "expression": {
                    "$": " AND ".join(expression_parts)
                },
                "parameter": parameters
            }
            
            resultado = self.load_records(
                entity="CabecalhoNota",
                fields="NUNOTA,CODPARC,DTNEG,VLRNOTA,STATUSNOTA,OBSERVACAO",
                criteria=criteria,
                limit=limite
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                pedidos = []
                for entity in entity_list:
                    pedido = {
                        'nunota': self._extract_value(entity.get('f0')),
                        'codparc': self._extract_value(entity.get('f1')),
                        'dtneg': self._extract_value(entity.get('f2')),
                        'vlrnota': self._extract_value(entity.get('f3')),
                        'status': self._extract_value(entity.get('f4')),
                        'observacao': self._extract_value(entity.get('f5'))
                    }
                    pedidos.append(pedido)
                
                return {
                    'total': total,
                    'pedidos': pedidos,
                    'filtros_aplicados': filtros
                }
            
            return {'total': 0, 'pedidos': [], 'filtros_aplicados': filtros}
            
        except Exception as e:
            print(f"[PEDIDOS] Erro ao listar todos os pedidos: {e}")
            return {'total': 0, 'pedidos': [], 'erro': str(e)}
    
    def obter_itens_pedido(self, nunota):
        """
        Obtém itens de um pedido específico
        """
        try:
            criteria = {
                "expression": {
                    "$": "this.NUNOTA = ?"
                },
                "parameter": [
                    {
                        "type": "I",
                        "value": str(nunota)
                    }
                ]
            }
            
            resultado = self.load_records(
                entity="ItemNota",
                fields="SEQUENCIA,CODPROD,QTDNEG,VLRUNIT,VLRTOT,CODLOCALORIG,CODVOL",
                criteria=criteria
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                itens = []
                for entity in entity_list:
                    item = {
                        'sequencia': self._extract_value(entity.get('f0')),
                        'codprod': self._extract_value(entity.get('f1')),
                        'qtdneg': self._extract_value(entity.get('f2')),
                        'vlrunit': self._extract_value(entity.get('f3')),
                        'vlrtot': self._extract_value(entity.get('f4')),
                        'codlocalorig': self._extract_value(entity.get('f5')),
                        'codvol': self._extract_value(entity.get('f6'))
                    }
                    itens.append(item)
                
                return {
                    'encontrado': True,
                    'nunota': nunota,
                    'total_itens': total,
                    'itens': itens
                }
            
            return {'encontrado': False, 'nunota': nunota}
            
        except Exception as e:
            print(f"[PEDIDOS] Erro ao obter itens do pedido: {e}")
            return {'encontrado': False, 'erro': str(e)}
    
    def validar_pedido_completo(self, nunota):
        """
        Valida se um pedido está completo e consistente
        """
        try:
            # Busca dados do cabeçalho
            pedido = self.consultar(nunota)
            if not pedido.get('encontrado', False):
                return {
                    'valido': False,
                    'erro': 'Pedido não encontrado'
                }
            
            # Busca itens do pedido
            itens_result = self.obter_itens_pedido(nunota)
            if not itens_result.get('encontrado', False):
                return {
                    'valido': False,
                    'erro': 'Itens do pedido não encontrados'
                }
            
            itens = itens_result['itens']
            problemas_validacao = []
            
            # Validações do cabeçalho
            if not pedido.get('codparc'):
                problemas_validacao.append("CODPARC não informado")
            
            if not pedido.get('dtneg'):
                problemas_validacao.append("Data de negociação não informada")
            
            # Validações dos itens
            if not itens or len(itens) == 0:
                problemas_validacao.append("Pedido sem itens")
            else:
                for i, item in enumerate(itens):
                    if not item.get('codprod'):
                        problemas_validacao.append(f"Item {i+1}: CODPROD não informado")
                    
                    if not item.get('qtdneg') or float(item.get('qtdneg', 0)) <= 0:
                        problemas_validacao.append(f"Item {i+1}: Quantidade inválida")
                    
                    if not item.get('codlocalorig'):
                        problemas_validacao.append(f"Item {i+1}: CODLOCALORIG não informado")
            
            # Resultado da validação
            valido = len(problemas_validacao) == 0
            
            resultado_validacao = {
                'valido': valido,
                'nunota': nunota,
                'total_itens': len(itens),
                'problemas': problemas_validacao,
                'dados_pedido': pedido,
                'dados_itens': itens
            }
            
            if valido:
                print(f"[PEDIDOS] Pedido {nunota} válido com {len(itens)} itens")
            else:
                print(f"[PEDIDOS] Pedido {nunota} inválido:")
                for problema in problemas_validacao:
                    print(f"[PEDIDOS]   - {problema}")
            
            return resultado_validacao
            
        except Exception as e:
            print(f"[PEDIDOS] Erro na validação do pedido: {e}")
            return {
                'valido': False,
                'erro': str(e)
            }

    def _mapear_frete_por_estoque_msc(self, raw_woo_payload):
        """
        Mapeia o valor do frete dividido por CODLOCALORIG, 
        baseado no meta_data _msc_codlocal_groups e nas shipping_lines.
        Assume correspondência 1:1 entre grupos e linhas de frete (ordem/tamanho).
        """
        frete_por_estoque = {}
        
        # 1. Obter grupos de estoque (CODLOCALORIG)
        msc_groups_meta = [m.get('value') for m in raw_woo_payload.get('meta_data', []) if m.get('key') == '_msc_codlocal_groups']
        shipping_lines = raw_woo_payload.get('shipping_lines', [])

        if not msc_groups_meta:
            print("[PEDIDOS] Metadata _msc_codlocal_groups não encontrada.")
            return {}

        try:
            msc_groups_value = msc_groups_meta[0] 
            # Meta pode ser string JSON
            if isinstance(msc_groups_value, str):
                msc_groups = json.loads(msc_groups_value)
            else:
                msc_groups = msc_groups_value
        except Exception as e:
            print(f"[PEDIDOS] Erro ao parsear _msc_codlocal_groups: {e}")
            return {}

        if len(msc_groups) == len(shipping_lines):
            stock_keys = list(msc_groups.keys())
            
            # Associa a linha de frete ao grupo de estoque (codlocal)
            for i, stock_key in enumerate(stock_keys):
                frete_amount = float(shipping_lines[i].get('total', 0))
                frete_por_estoque[stock_key] = frete_amount
            
            print(f"[PEDIDOS] Frete mapeado por estoque (ordem implícita): {frete_por_estoque}")
            return frete_por_estoque
            
        else:
            print(f"[PEDIDOS] Número de grupos ({len(msc_groups)}) não corresponde ao número de linhas de frete ({len(shipping_lines)}). Retornando zero para itens.")
            return {}
    
    def _extract_value(self, field_obj):
        """
        CORRIGIDO: Extrai valor do objeto de campo do Sankhya de forma mais robusta
        """
        if not field_obj:
            return ""
        
        if isinstance(field_obj, dict):
            return field_obj.get('$', '')
        
        return str(field_obj) if field_obj is not None else ""
