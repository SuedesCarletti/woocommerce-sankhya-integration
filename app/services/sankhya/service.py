# app/services/sankhya/service.py - VERSÃO CORRIGIDA
"""
SankhyaService CORRIGIDO - Remove imports com prefixo 'app.' que causam erro
Versão: 2.7.0 - Correção de imports circulares
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import re
import tempfile
import os
import base64

# CORREÇÃO 1: Imports relativos ao invés de 'from app.services...'
from .base import SankhyaClient
from .auth import SankhyaAuth
from .parceiros import ParceirosService
from .pedidos import PedidosService
from .produtos import ProdutosService
from .transportadoras import TransportadorasService

# CORREÇÃO 2: Import de config sem prefixo app
from config.settings import get_sankhya_defaults

# CORREÇÃO 3: Import condicional do customer integration
try:
    from .customers_mapping_secure import CustomerValidationServiceFinal
    CUSTOMER_INTEGRATION_AVAILABLE = True
except ImportError:
    CUSTOMER_INTEGRATION_AVAILABLE = False
    print("[SANKHYA SERVICE] Customer integration não disponível")

# Import condicional do BrazilFiscalReport
try:
    from brazilfiscalreport.danfe import Danfe
    DANFE_AVAILABLE = True
except ImportError:
    DANFE_AVAILABLE = False

logger = logging.getLogger(__name__)


class SankhyaService:
    """Serviço principal para integração com Sankhya ERP"""
    
    def __init__(self, token=None):
        """
        Inicializa o serviço Sankhya
        
        Args:
            token: Token de autenticação (opcional)
        """
        self.token = token
        
        if token:
            try:
                print(f"[SANKHYA SERVICE] Inicializando serviços...")
                
                # Inicializar serviços principais
                self.parceiros = ParceirosService(token)
                self.pedidos = PedidosService(token)
                self.produtos = ProdutosService(token)
                self.transportadoras = TransportadorasService(token)
                
                # Inicializar customer integration se disponível
                if CUSTOMER_INTEGRATION_AVAILABLE:
                    try:
                        self.customer_integration = CustomerValidationServiceFinal(token)
                        print(f"[CUSTOMER VALIDATION FINAL] Serviço inicializado com sucesso")
                    except Exception as e:
                        print(f"[CUSTOMER VALIDATION FINAL] Erro: {e}")
                        self.customer_integration = None
                else:
                    self.customer_integration = None
                
                print(f"[SANKHYA SERVICE] Customer integration carregado com sucesso")
                print(f"[SANKHYA SERVICE] Serviços principais inicializados com sucesso")
                print(f"[SANKHYA SERVICE] Customer integration: {'Ativo' if self.customer_integration else 'Inativo'}")
                print(f"[SANKHYA SERVICE] Status dos serviços:")
                print(f"[SANKHYA SERVICE]   token_valido: {bool(self.token)}")
                print(f"[SANKHYA SERVICE]   parceiros_service: {bool(self.parceiros)}")
                print(f"[SANKHYA SERVICE]   pedidos_service: {bool(self.pedidos)}")
                print(f"[SANKHYA SERVICE]   produtos_service: {bool(self.produtos)}")
                print(f"[SANKHYA SERVICE]   transportadoras_service: {bool(self.transportadoras)}")
                
            except Exception as e:
                print(f"[SANKHYA SERVICE] Erro ao inicializar serviços: {e}")
                raise
        else:
            self.parceiros = None
            self.pedidos = None
            self.produtos = None
            self.transportadoras = None
            self.customer_integration = None
    
    @classmethod
    def with_auth(cls):
        """Context manager para autenticação automática"""
        return SankhyaServiceContext()
    
    # MÉTODOS DE NFe
    
    def _obter_nunota_faturamento_por_id_woocommerce(self, id_woocommerce: int) -> Optional[int]:
        """
        Busca o NUNOTA da Nota Fiscal de Venda (TIPMOV='V') associado ao ID do WooCommerce.
        Usa SQL direto para evitar problemas de tipagem (Int vs String) no loadRecords.
        """
        try:
            client = SankhyaClient(self.token)
            
            # Query SQL direta, superando limitações do MGE
            sql = (
                f"SELECT NUNOTA FROM TGFCAB "
                f"WHERE AD_IDWOOCOMMERCE = {int(id_woocommerce)} "
                f"AND TIPMOV = 'V'"
            )
            
            response = client.execute_query(sql)
            status = response.get("status", "0")
            rows = response.get("responseBody", {}).get("rows", [])
            
            if status == "1" and rows:
                row = rows[0] if isinstance(rows, list) else rows
                
                # O Sankhya executeQuery retorna arrays de valores (ex: [[8668589]]) 
                # ao invés de dicionários quando não há metadados explícitos no formato.
                valor_nunota = None
                if isinstance(row, list) and len(row) > 0:
                    valor_nunota = row[0]
                elif isinstance(row, dict):
                    valor_nunota = row.get("NUNOTA", {}).get("$", "") or row.get("NUNOTA", "")
                
                if valor_nunota:
                    logger.info(f"[NUNOTA Faturamento] Encontrado {valor_nunota} via SQL para pedido #{id_woocommerce}")
                    return int(valor_nunota)
            
            logger.warning(f"[NUNOTA Faturamento] Nenhum TIPMOV='V' encontrado para pedido #{id_woocommerce}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar NUNOTA de faturamento via SQL: {e}", exc_info=True)
            return None


    def obter_nunota_por_id_woocommerce(self, id_woocommerce: int) -> Optional[int]:
        """
        Busca NUNOTA pelo ID do pedido WooCommerce
        
        Args:
            id_woocommerce: ID do pedido no WooCommerce
            
        Returns:
            int: NUNOTA encontrado ou None
        """
        try:
            logger.info(f"[NUNOTA] Buscando para ID WooCommerce: {id_woocommerce}")
            
            # SankhyaClient já foi importado
            client = SankhyaClient(self.token)
            
            # FIX: Restructure criteria for client.load_records
            criteria = {
                "expression": {"$": "this.AD_IDWOOCOMMERCE = ?"},
                "parameter": [{
                    "type": "I", 
                    "$": str(id_woocommerce) # Use '$' for value in load_records parameters
                }]
            }
            
            # FIX: Use client.load_records instead of client.call_service
            response = client.load_records(
                entity="CabecalhoNota",
                fields="NUNOTA", # Busca apenas o NUNOTA
                criteria=criteria,
                limit=1
            )
            
            # FIX: Adjust response parsing based on load_records structure (f0, f1, ...)
            entities = response.get("responseBody", {}).get("entities", {})
            
            if int(entities.get("total", "0")) == 0:
                logger.warning(f"[NUNOTA] Nenhuma nota encontrada para ID WooCommerce {id_woocommerce}")
                return None
            
            entity = entities.get("entity")
            if isinstance(entity, list):
                entity = entity[0]
            
            # NUNOTA está no f0 (primeiro campo do fieldset)
            nunota = entity.get('f0', {}).get('$')
            
            if nunota:
                logger.info(f"[NUNOTA] Encontrado: {nunota}")
                return int(nunota)
            else:
                logger.warning(f"[NUNOTA] NUNOTA encontrado, mas valor está vazio no registro.")
                return None
            
        except Exception as e:
            logger.error(f"[NUNOTA] Erro: {e}", exc_info=True)
            return None

    def _obter_xml_nfe_por_nunota(self, nunota: int, order_id: int = None) -> str:
            """
            Obtém o XML da NFe consultando diretamente TGFNFE via SQL.

            O loadRecords na entidade ArquivoNfe falha silenciosamente para
            campos CLOB (retorna total=0 mesmo com dados). Usamos
            DbExplorerSP.executeInternalQuery para buscar diretamente.

            Prioridade de campos:
              1. XMLENVCLI  → nfeProc completo (NFe + protocolo SEFAZ) — ideal para DANFE
              2. XML        → NFe pura (sem protocolo), aceita por brazilfiscalreport
            """
            try:
                logger.info(f"[XML NFe] Buscando XML via SQL em TGFNFE para NUNOTA {nunota}")

                client = SankhyaClient(self.token)

                # ── Estratégia 1: SQL direto via DbExplorerSP (contorna CLOB) ──
                sql = (
                    f"SELECT XMLENVCLI, XML FROM TGFNFE "
                    f"WHERE NUNOTA = {int(nunota)}"
                )
                response = client.execute_query(sql)

                status = response.get("status", "0")
                rows = response.get("responseBody", {}).get("rows", [])

                if status == "1" and rows:
                    row = rows[0] if isinstance(rows, list) else rows
                    
                    xml_content = ""
                    
                    # Se retornar lista simples de valores (comportamento do executeQuery)
                    if isinstance(row, list) and len(row) >= 2:
                        xml_content = row[0] or row[1] # Tenta XMLENVCLI, senão XML
                    
                    # Se retornar dicionário
                    elif isinstance(row, dict):
                        xml_content = (
                            row.get("XMLENVCLI", {}).get("$", "") or row.get("XMLENVCLI", "")
                        )
                        if not xml_content:
                            xml_content = (
                                row.get("XML", {}).get("$", "") or row.get("XML", "")
                            )

                    if xml_content and len(xml_content) > 100:
                        logger.info(
                            f"[XML NFe] XML obtido via SQL da TGFNFE "
                            f"para NUNOTA {nunota} — {len(xml_content)} chars"
                        )
                        return xml_content.strip()

                logger.warning(
                    f"⚠️ [XML NFe] SQL não retornou XML para NUNOTA {nunota}. "
                    f"Tentando loadRecords em ArquivoNfe como fallback..."
                )

                # ── Estratégia 2: loadRecords na entidade ArquivoNfe (legado) ──
                criteria = {
                    "expression": {"$": "this.NUNOTA = ?"},
                    "parameter": [{"$": str(nunota), "type": "I"}]
                }
                response2 = client.load_records(
                    entity="ArquivoNfe",
                    fields="XML",
                    criteria=criteria,
                    limit=1
                )
                entities = response2.get("responseBody", {}).get("entities", {})
                total = int(entities.get("total", "0"))

                if total > 0:
                    entity = entities.get("entity")
                    if isinstance(entity, list):
                        entity = entity[0]
                    xml_content = entity.get("f0", {}).get("$", "")
                    if xml_content and len(xml_content) > 100:
                        logger.info(
                            f"[XML NFe] XML obtido via ArquivoNfe "
                            f"para NUNOTA {nunota} — {len(xml_content)} chars"
                        )
                        return xml_content.strip()

                # ── Estratégia 3: Fallback para NUNOTA de faturamento ──
                if order_id:
                    logger.info(
                        f"📄 [XML NFe] NUNOTA {nunota} sem XML. "
                        f"Tentando NUNOTA de faturamento para Pedido #{order_id}"
                    )
                    nunota_faturamento = self._obter_nunota_faturamento_por_id_woocommerce(order_id)
                    if nunota_faturamento and str(nunota_faturamento) != str(nunota):
                        logger.info(
                            f"📄 [XML NFe] Encontrado faturamento NUNOTA {nunota_faturamento}. "
                            f"Buscando XML..."
                        )
                        return self._obter_xml_nfe_por_nunota(nunota_faturamento)

                raise Exception(f"Registro de XML não encontrado na TGFNFE para NUNOTA {nunota}")

            except Exception as e:
                logger.error(f"[XML NFe] Erro ao obter XML da TGFNFE: {e}", exc_info=True)
                raise


    # FUNÇÃO 2: GERAR PDF (VERSÃO MELHORADA)
    
    # Correção do método obter_danfe_pdf - service.py linha ~260-310
    
    def obter_danfe_pdf(self, nunota: int) -> bytes:
        """
        Gera o DANFE PDF a partir do XMLNFE do Sankhya
        VERSÃO MELHORADA com logs e validações
        """
        logger.info(f"[DANFE] Gerando PDF para NUNOTA={nunota}")
    
        try:
            # ETAPA 1: Obter XML do Sankhya
            logger.debug(f"[DANFE] Buscando XML no Sankhya...")
            xml_content = self._obter_xml_nfe_por_nunota(nunota)
            
            # Validações
            if not xml_content:
                raise FileNotFoundError(f"XML não disponível para NUNOTA {nunota}")
            
            if len(xml_content) < 100:
                raise ValueError(f"XML muito pequeno ({len(xml_content)} chars)")
            
            xml_limpo = xml_content.strip()
            if not xml_limpo.startswith('<?xml'):
                raise ValueError(f"Conteúdo não é XML válido. Início: {xml_limpo[:100]}")
            
            logger.info(f"[DANFE] XML obtido - {len(xml_content)} chars")
            logger.debug(f"[DANFE] Preview: {xml_content[:500]}")
    
            # ETAPA 2: Gerar PDF
            logger.debug(f"[DANFE] Iniciando geração com BrazilFiscalReport...")
            
            # Importar biblioteca (captura erro se não instalada)
            try:
                from brazilfiscalreport.danfe import Danfe
            except ImportError as e:
                logger.error(f"[DANFE] Biblioteca não instalada: {e}")
                raise ImportError(
                    "BrazilFiscalReport não encontrada. "
                    "Execute: pip install BrazilFiscalReport==0.4.1"
                )
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                temp_pdf_path = tmp.name
                logger.debug(f"[DANFE] Arquivo temp: {temp_pdf_path}")
            
            try:
                # Gerar DANFE
                logger.debug("[DANFE] Renderizando PDF...")
                danfe = Danfe(xml=xml_content, config=None)
                danfe.output(temp_pdf_path)
                
                # Verificar se arquivo foi criado
                if not os.path.exists(temp_pdf_path):
                    raise RuntimeError(f"Arquivo PDF não foi criado")
                
                file_size = os.path.getsize(temp_pdf_path)
                if file_size == 0:
                    raise ValueError("PDF gerado está vazio")
                
                logger.info(f"[DANFE] PDF criado - {file_size} bytes")
                
            except Exception as e:
                # Limpar arquivo em caso de erro
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
                raise RuntimeError(f"Erro ao gerar PDF: {str(e)}")
    
            # ETAPA 3: Ler arquivo em memória
            logger.debug(f"[DANFE] Lendo PDF...")
            try:
                with open(temp_pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
            except Exception as e:
                raise IOError(f"Erro ao ler PDF: {str(e)}")
            finally:
                # Sempre limpar arquivo temporário
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
                    logger.debug(f"[DANFE] Arquivo temp removido")
            
            # Validação final
            if not pdf_bytes or len(pdf_bytes) == 0:
                raise ValueError("PDF resultou em conteúdo vazio")
            
            if not pdf_bytes.startswith(b'%PDF'):
                raise ValueError("Arquivo gerado não é um PDF válido")
            
            logger.info(f"[DANFE] SUCESSO - {len(pdf_bytes)} bytes")
            return pdf_bytes
    
        except FileNotFoundError as e:
            logger.error(f"[DANFE] NFe não encontrada: {e}")
            raise
        except (ValueError, ImportError, IOError, RuntimeError) as e:
            logger.error(f"[DANFE] Erro: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"[DANFE] Erro inesperado: {e}", exc_info=True)
            raise ValueError(f"Falha: {str(e)}")
    
    # MÉTODOS DE PROCESSAMENTO DE WEBHOOKS
    
    def processar_webhook(self, headers, payload):
        """
        Método principal para processar webhooks do WooCommerce
        
        Args:
            headers: Dicionário com headers do webhook
            payload: Dados do webhook (pedido, cliente, etc)
            
        Returns:
            Dicionário com status da operação
        """
        try:
            event_type = headers.get('event_type', '')
            resource = headers.get('resource', '')
            
            print(f"[SANKHYA SERVICE] Webhook recebido: {resource}.{event_type}")
            
            if resource == 'order' and event_type == 'created':
                return self._processar_pedido_criado(payload)
            elif resource == 'order' and event_type == 'updated':
                return self._processar_pedido_atualizado(payload)
            else:
                print(f"[SANKHYA SERVICE] ℹEvento não processado: {resource}.{event_type}")
                return {
                    "status": "skipped",
                    "message": f"Evento {resource}.{event_type} não processado"
                }
        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro no processamento do webhook: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _processar_pedido_criado(self, payload):
        """
        Processa pedido criado do WooCommerce
        
        Fluxo:
        1. Validações básicas
        2. Diagnóstico dos produtos
        3. Processamento do cliente
        4. Processamento da transportadora
        5. Montagem dos itens
        6. Inclusão do pedido no Sankhya
        
        Args:
            payload: Dados do pedido do WooCommerce
            
        Returns:
            Dicionário com status da operação
        """
        try:
            pedido_id = payload.get('id', 0)
            print(f"[SANKHYA SERVICE] Processando pedido criado: {pedido_id}")
            
            # VALIDAÇÃO 1: Dados básicos do pedido
            if not pedido_id or pedido_id <= 0:
                return {
                    "status": "error",
                    "error": "ID do pedido inválido",
                    "pedido_id": pedido_id
                }
            
            # VALIDAÇÃO 2: Dados do cliente
            billing = payload.get('billing', {})
            if not billing:
                return {
                    "status": "error",
                    "error": "Dados de billing não encontrados",
                    "pedido_id": pedido_id
                }
            
            # VALIDAÇÃO 3: Produtos do pedido
            produtos_wc = payload.get('line_items', [])
            if not produtos_wc or len(produtos_wc) == 0:
                return {
                    "status": "error",
                    "error": "Nenhum produto encontrado no pedido",
                    "pedido_id": pedido_id
                }
            
            # VALIDAÇÃO 4: Diagnóstico dos produtos
            produtos_wc = payload.get('line_items', [])
            print(f"[SANKHYA SERVICE] Diagnosticando produtos...")
            diagnostico = self._diagnosticar_pedido_completo(produtos_wc)
            
            if not diagnostico.get('pode_processar', False):
                # ... (error handling)
                pass
            
            # PROCESSAMENTO 1: Cliente
            print(f"[SANKHYA SERVICE] Processando cliente completo...")
            resultado_cliente = self._processar_cliente_completo(payload)
            
            if not resultado_cliente.get('sucesso'):
                return {
                    "status": "error",
                    "error": f"Erro no cliente: {resultado_cliente.get('erro')}",
                    "pedido_id": pedido_id
                }
            
            parceiro_id = resultado_cliente['parceiro_id']
            print(f"[SANKHYA SERVICE] Parceiro: {parceiro_id} - {resultado_cliente.get('nome_parceiro', '')}")
            
            # PROCESSAMENTO 2: Transportadora (apenas busca CODPARC)
            transportadora_info = self._processar_transportadora(payload)
            
            # PROCESSAMENTO 3: Montar estrutura do pedido
            dtneg = datetime.now().strftime('%Y-%m-%d')

            # --- START: FREIGHT RATING E ALOCAÇÃO ---
            
            # 1. Mapeia CODLOCAL do plugin e Frete total por grupo
            frete_por_codlocal = self._mapear_frete_por_codlocal(payload)
            item_codlocal_map = self._mapear_item_para_codlocal(payload)
            
            itens_com_frete_rateado = []
            itens_agrupados_por_codlocal = {}

            # Agrupar itens por CODLOCALORIG determinado (pelo plugin ou diagnóstico)
            for item_wc in produtos_wc:
                product_id = str(item_wc.get('product_id', 0))
                # 1. Tenta CODLOCAL do plugin
                codlocal = item_codlocal_map.get(product_id)
                # 2. Se falhar, usa o do diagnóstico (que usou estoque Sankhya)
                if not codlocal:
                     codlocal = diagnostico.get('mapa_itens', {}).get(str(item_wc.get('id', '')), {}).get('codlocalorig')
                
                if codlocal:
                    if codlocal not in itens_agrupados_por_codlocal:
                        itens_agrupados_por_codlocal[codlocal] = []
                    item_wc['codlocalorig'] = codlocal # Temporário
                    itens_agrupados_por_codlocal[codlocal].append(item_wc)
                # else: item sem codlocal será ignorado se não puder ser mapeado 

            # Realizar rateio (cubagem/valor) dentro de cada grupo de frete
            for codlocal, items_grupo in itens_agrupados_por_codlocal.items():
                frete_total_grupo = frete_por_codlocal.get(codlocal, 0.0) if frete_por_codlocal else float(payload.get('shipping_total', 0))
                
                if frete_total_grupo > 0:
                    print(f"[SANKHYA SERVICE] Rateando R$ {frete_total_grupo:.2f} para o estoque {codlocal}")
                    
                    # Usa o rateio de cubagem (mesmo que caia no fallback de quantidade/valor)
                    rated_freight = self.pedidos.calcular_rateio_frete_cubagem(items_grupo, frete_total_grupo)
                    
                    # Juntar resultados
                    for rated_item in rated_freight:
                         # Encontra o item original (usando product_id como chave de join)
                         item_wc = next(i for i in produtos_wc if str(i.get('product_id')) == str(rated_item['product_id']))
                         item_wc['vlr_frete_rateado'] = rated_item['vlr_frete_rateado']
                         item_wc['codlocalorig'] = codlocal # Finaliza o codlocal
                         itens_com_frete_rateado.append(item_wc)

                else:
                    # Sem frete para este grupo
                    for item in items_grupo:
                        item['vlr_frete_rateado'] = 0.0
                        item['codlocalorig'] = codlocal
                        itens_com_frete_rateado.append(item)
            
            # --- END: FREIGHT RATING E ALOCAÇÃO ---
            
            # Montar itens do pedido USANDO itens_com_frete_rateado (Garantindo itens limpos)
            itens_pedido = []
            mapa_itens = diagnostico.get('mapa_itens', {})
            
            for item_wc in itens_com_frete_rateado:
                item_id = str(item_wc.get('id', ''))
                
                if item_id in mapa_itens and mapa_itens[item_id].get('pode_processar', False):
                    item_info = mapa_itens[item_id]
                    
                    item_pedido = {
                        'codprod': item_info['codprod'],
                        'qtdneg': float(item_wc.get('quantity', 1)),
                        'codlocalorig': item_wc.get('codlocalorig', item_info.get('codlocalorig', '1001')),
                        'codvol': item_info.get('codvol', 'UN'),
                        'vlrunit': float(item_wc.get('price', 0)), # PREÇO LIMPO
                        'vlrtot': float(item_wc.get('total', 0)), # TOTAL LIMPO
                        'vlr_frete_rateado': item_wc.get('vlr_frete_rateado', 0.0) # Frete para AD_VLRFRETEECOMMERCE
                    }
                    itens_pedido.append(item_pedido)
                    print(f"[SANKHYA SERVICE] Item {item_id} adicionado (Frete R: R$ {item_pedido['vlr_frete_rateado']:.2f})")
            
            if not itens_pedido:
                return {
                    "status": "error",
                    "error": "Nenhum item válido para processamento",
                    "pedido_id": pedido_id
                }
            
            print(f"[SANKHYA SERVICE] {len(itens_pedido)} itens serão incluídos no pedido")
            
            # Kwargs do pedido
            kwargs_pedido = {
                'informar_preco': True,
                'observacoes': f"Pedido importado do WooCommerce - ID: {pedido_id}",
                'id_woo': pedido_id,
                'dados_cliente': payload, 
                'raw_woo_payload': payload # CRITICAL: Passar payload bruto
            }
            
            # Adicionar transportadora (o valor do frete no cabeçalho será determinado pela PedidosService)
            if transportadora_info.get('transportadora_encontrada'):
                kwargs_pedido['codparctransp'] = transportadora_info['codparc_transportadora']

            # Sempre passar o valor do frete, mesmo que a transportadora não tenha sido mapeada
            if transportadora_info.get('valor_frete') is not None:
                kwargs_pedido['vlr_frete'] = transportadora_info.get('valor_frete')

            # INCLUIR PEDIDO
            print(f"[SANKHYA SERVICE] Incluindo pedido no Sankhya...")
            resultado_pedido = self.pedidos.incluir(
                codparc=parceiro_id,
                dtneg=dtneg,
                itens=itens_pedido,
                **kwargs_pedido
            )
            
            if not resultado_pedido.get('sucesso'):
                return {
                    "status": "error",
                    "error": resultado_pedido.get('erro', 'Erro desconhecido'),
                    "pedido_id": pedido_id
                }
            
  # Verificar se foram criados múltiplos pedidos
            if resultado_pedido.get('multiplos_pedidos', False):
                nunotas_lista = resultado_pedido.get('nunotas', [])
                print(f"[SANKHYA SERVICE] Múltiplos pedidos criados: {len(nunotas_lista)}")
                
                # Salvar TODOS os NUNOTAs no WooCommerce
                sucesso_salvamento = self._salvar_multiplos_nunotas_woocommerce(
                    pedido_id, 
                    nunotas_lista
                )
                
                return {
                    "status": "success",
                    "pedido_woo": pedido_id,
                    "multiplos_pedidos": True,
                    "nunotas": nunotas_lista,
                    "total_pedidos": len(nunotas_lista),
                    "mensagem": resultado_pedido.get('mensagem'),
                    "salvamento_woo": sucesso_salvamento
                }
            
            else:
                # Pedido único (fluxo original)
                nunota = resultado_pedido.get('nunota')
                print(f"[SANKHYA SERVICE] Pedido único criado: NUNOTA {nunota}")
                
                # Salvar NUNOTA no WooCommerce (MANTER CÓDIGO EXISTENTE)
                sucesso_salvamento = self._salvar_nunota_woocommerce(pedido_id, nunota)
                
                return {
                    "status": "success",
                    "pedido_woo": pedido_id,
                    "nunota": nunota,
                    "mensagem": resultado_pedido.get('mensagem'),
                    "salvamento_woo": sucesso_salvamento
                }

        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro no processamento do pedido criado: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pedido_id": payload.get('id', 0)
            }

    def _processar_pedido_atualizado(self, payload):
        """
        Processa pedido atualizado do WooCommerce
        
        Args:
            payload: Dados do pedido atualizado
            
        Returns:
            Dicionário com status da operação
        """
        try:
            pedido_id = payload.get('id', 0)
            status_atual = payload.get('status', '')
            
            print(f"[SANKHYA SERVICE] Processando pedido atualizado: {pedido_id}")
            print(f"[SANKHYA SERVICE] Status atual: {status_atual}")
            
            # Mapeia ações baseadas no status
            mapeamento_status = {
                'pending': 'monitorar',
                'processing': 'processar_como_novo',
                'on-hold': 'monitorar',
                'completed': 'monitorar',
                'cancelled': 'cancelar',
                'refunded': 'estornar',
                'failed': 'falhar'
            }
            
            acao = mapeamento_status.get(status_atual, 'monitorar')
            print(f"[SANKHYA SERVICE] Ação definida: {acao}")
            
            if acao == 'processar_como_novo':
                print(f"[SANKHYA SERVICE] Processando pedido {pedido_id} como novo devido ao status '{status_atual}'")
                return self._processar_pedido_criado(payload)
            elif acao == 'monitorar':
                print(f"[SANKHYA SERVICE] Monitorando pedido {pedido_id} com status '{status_atual}'")
                return {
                    "status": "success",
                    "message": f"Pedido {pedido_id} sendo monitorado com status {status_atual}",
                    "action": "monitored"
                }
            else:
                print(f"[SANKHYA SERVICE] Status '{status_atual}' não mapeado")
                return {
                    "status": "success",
                    "message": f"Pedido {pedido_id} com status não mapeado: {status_atual}",
                    "action": "logged"
                }
        
        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro no processamento do pedido atualizado: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    # MÉTODOS AUXILIARES DE DIAGNÓSTICO
    
    def _diagnosticar_pedido_completo(self, produtos_wc):
        """
        Diagnostica se todos os produtos do pedido podem ser processados
        [...] (Corpo da função)
        """
        try:
            total_itens = len(produtos_wc)
            mapa_itens = {}
            itens_validos = 0
            itens_problematicos = 0
            problemas = []
            
            print(f"[SANKHYA SERVICE] Diagnosticando {total_itens} produtos...")
            
            for i, item in enumerate(produtos_wc):
                # Validação: item deve ser um dicionário
                if not isinstance(item, dict):
                    problema = f"Item {i}: Formato inválido (não é dicionário)"
                    problemas.append(problema)
                    itens_problematicos += 1
                    print(f"[SANKHYA SERVICE] {problema}")
                    continue
                
                item_id = str(item.get('id', f'unknown_{i}'))
                sku = item.get('sku', '').strip()
                product_id = item.get('product_id', 0)
                nome_produto = item.get('name', 'Sem nome')
                
                print(f"[SANKHYA SERVICE] Analisando item {i+1}/{total_itens}: {nome_produto}")
                print(f"[SANKHYA SERVICE]   Item ID: {item_id}")
                print(f"[SANKHYA SERVICE]   SKU: {sku if sku else '(vazio)'}")
                print(f"[SANKHYA SERVICE]   Product ID: {product_id}")
                
                try:
                    # Validação: precisa de SKU ou Product ID
                    if not sku and not product_id:
                        problema = f"Item {item_id}: SKU e Product ID vazios"
                        problemas.append(problema)
                        mapa_itens[item_id] = {
                            'pode_processar': False,
                            'erro': 'SKU e Product ID vazios'
                        }
                        itens_problematicos += 1
                        print(f"[SANKHYA SERVICE] {problema}")
                        continue
                    
                    # FIX: Utilizar o método robusto mapear_produto da ProdutosService
                    produto_mapeado = self.produtos.mapear_produto(item)

                    if produto_mapeado and produto_mapeado.get('produto_encontrado', False):
                        codprod = produto_mapeado.get('codprod_sankhya') or produto_mapeado.get('CODPROD')

                        if not codprod:
                             raise ValueError("CODPROD Sankhya não encontrado após mapeamento.")

                        # Obtém CODLOCALORIG dinmico
                        codlocalorig = self.pedidos.obter_codlocalorig_dinamico(codprod)
                        if not codlocalorig:
                            codlocalorig = '1001' # Fallback padrão
                        
                        mapa_itens[item_id] = {
                            'pode_processar': True,
                            'codprod': codprod,
                            'codlocalorig': codlocalorig,
                            'codvol': produto_mapeado.get('CODVOL', 'UN'),
                            'sku': sku,
                            'product_id': product_id,
                            'nome': nome_produto
                        }
                        itens_validos += 1
                        print(f"[SANKHYA SERVICE] Item {item_id} mapeado com sucesso")
                    else:
                        # Erro - produto não encontrado
                        problema = f"Item {item_id} ({nome_produto}): Produto não encontrado no Sankhya"
                        problemas.append(problema)
                        mapa_itens[item_id] = {
                            'pode_processar': False,
                            'erro': produto_mapeado.get('erro', 'Produto não encontrado no Sankhya') if produto_mapeado else 'Produto não encontrado no Sankhya',
                            'sku': sku,
                            'product_id': product_id,
                            'nome': nome_produto
                        }
                        itens_problematicos += 1
                        print(f"[SANKHYA SERVICE] {problema}")
                
                except Exception as e:
                    # Erro inesperado no processamento do item
                    problema = f"Item {item_id} ({nome_produto}): Erro no mapeamento - {str(e)}"
                    problemas.append(problema)
                    mapa_itens[item_id] = {
                        'pode_processar': False,
                        'erro': f'Erro no mapeamento: {str(e)}',
                        'sku': sku,
                        'product_id': product_id,
                        'nome': nome_produto
                    }
                    itens_problematicos += 1
                    print(f"[SANKHYA SERVICE] {problema}")
            
            # Determina se pode processar o pedido
            pode_processar = itens_validos > 0 and itens_problematicos == 0
            
            print(f"[SANKHYA SERVICE] RESULTADO DO DIAGNÓSTICO:")
            print(f"[SANKHYA SERVICE]   Total de itens: {total_itens}")
            print(f"[SANKHYA SERVICE]   Itens válidos: {itens_validos}")
            print(f"[SANKHYA SERVICE]   Itens problemáticos: {itens_problematicos}")
            print(f"[SANKHYA SERVICE]   Pode processar: {'SIM' if pode_processar else 'NÃO'}")
            
            if problemas:
                print(f"[SANKHYA SERVICE] Problemas encontrados:")
                for problema in problemas:
                    print(f"[SANKHYA SERVICE]     - {problema}")
            
            return {
                'pode_processar': pode_processar,
                'total_itens': total_itens,
                'itens_validos': itens_validos,
                'itens_problematicos': itens_problematicos,
                'problemas': problemas,
                'mapa_itens': mapa_itens
            }
            
        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro no diagnóstico: {e}")
            import traceback
            traceback.print_exc()
            return {
                'pode_processar': False,
                'total_itens': 0,
                'itens_validos': 0,
                'itens_problematicos': 0,
                'problemas': [f"Erro no diagnóstico: {str(e)}"],
                'mapa_itens': {}
            }

    def _mapear_frete_por_codlocal(self, payload):
        """
        Mapeia os totais das shipping_lines para o CODLOCALORIG correspondente,
        assumindo que há uma correspondência implícita via plugin multi-stock.
        """
        frete_por_estoque = {}
        
        msc_groups_meta = [m.get('value') for m in payload.get('meta_data', []) if m.get('key') == '_msc_codlocal_groups']
        shipping_lines = payload.get('shipping_lines', [])

        if not msc_groups_meta:
            return {}
        
        try:
            msc_groups_value = msc_groups_meta[0]
            if isinstance(msc_groups_value, str):
                # Tenta corrigir erro de string JSON
                msc_groups = json.loads(msc_groups_value)
            else:
                msc_groups = msc_groups_value
        except Exception:
            return {}

        if len(msc_groups) == len(shipping_lines):
            stock_keys = list(msc_groups.keys())
            
            # Associa a linha de frete ao grupo de estoque (codlocal)
            for i, stock_key in enumerate(stock_keys):
                frete_amount = float(shipping_lines[i].get('total', 0))
                frete_por_estoque[stock_key] = frete_amount
            
            print(f"[FRETE MAP] Mapeamento explícito de frete por estoque: {frete_por_estoque}")
            return frete_por_estoque
            
        return {}

    def _mapear_item_para_codlocal(self, payload):
        """
        Mapeia product_id para o CODLOCALORIG, usando o meta_data _msc_codlocal_groups.
        """
        item_codlocal_map = {}
        msc_groups_meta = [m.get('value') for m in payload.get('meta_data', []) if m.get('key') == '_msc_codlocal_groups']

        if not msc_groups_meta:
            return {} 

        try:
            msc_groups_value = msc_groups_meta[0]
            if isinstance(msc_groups_value, str):
                msc_groups = json.loads(msc_groups_value)
            else:
                msc_groups = msc_groups_value
        except Exception:
            return {}

        for codlocal, group_data in msc_groups.items():
            for item_data in group_data.get('items', []):
                # Usar product_id para mapear
                product_id = str(item_data.get('product_id'))
                item_codlocal_map[product_id] = codlocal
        
        return item_codlocal_map
    
    def _processar_cliente_completo(self, payload):
        """
        Processa cliente do WooCommerce (busca ou cadastra)
        
        Args:
            payload: Dados completos do pedido WooCommerce
            
        Returns:
            Dicionário com:
            - sucesso: bool
            - parceiro_id: int (se sucesso)
            - nome_parceiro: str (se sucesso)
            - acao: 'encontrado' ou 'cadastrado'
            - erro: str (se falha)
        """
        try:
            billing = payload.get('billing', {})
            
            # Informações básicas
            nome = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
            email = billing.get('email', '').strip()
            telefone = billing.get('phone', '').strip()
            
            print(f"[SANKHYA SERVICE] Processando cliente:")
            print(f"[SANKHYA SERVICE]   Nome: {nome}")
            print(f"[SANKHYA SERVICE]   Email: {email}")
            print(f"[SANKHYA SERVICE]   Telefone: {telefone}")
            
            # Documento (CPF/CNPJ)
            documento = self._extrair_documento_billing(billing, payload)
            
            if not documento:
                return {
                    'sucesso': False,
                    'erro': 'Documento (CPF/CNPJ) não encontrado'
                }
            
            documento_limpo = re.sub(r'\D', '', documento)
            print(f"[SANKHYA SERVICE]   Documento: {documento_limpo}")
            
            # Buscar parceiro no Sankhya
            print(f"[SANKHYA SERVICE] Buscando parceiro no Sankhya...")
            parceiro_existente = self.parceiros.consultar_por_documento(documento_limpo)
            
            if parceiro_existente:
                codparc = parceiro_existente.get('CODPARC')
                nomeparc = parceiro_existente.get('NOMEPARC', nome)
                print(f"[SANKHYA SERVICE] Parceiro encontrado: {codparc} - {nomeparc}")
                return {
                    'sucesso': True,
                    'parceiro_id': codparc,
                    'nome_parceiro': nomeparc,
                    'acao': 'encontrado'
                }
            else:
                print(f"[SANKHYA SERVICE] ℹParceiro não encontrado, tentando cadastrar...")
                
                # Se não encontrado e temos customer integration, cadastra
                if self.customer_integration:
                    resultado_cadastro = self.customer_integration.processar_cliente_completo(payload)
                    
                    if resultado_cadastro.get('sucesso_geral'):
                        codparc = resultado_cadastro.get('codparc_sankhya')
                        nomeparc = resultado_cadastro.get('nome_parceiro', nome)
                        print(f"[SANKHYA SERVICE] Parceiro cadastrado: {codparc} - {nomeparc}")
                        return {
                            'sucesso': True,
                            'parceiro_id': codparc,
                            'nome_parceiro': nomeparc,
                            'acao': 'cadastrado'
                        }
                    else:
                        erro = resultado_cadastro.get('erro', 'Falha ao cadastrar cliente')
                        print(f"[SANKHYA SERVICE] Erro no cadastro: {erro}")
                        return {
                            'sucesso': False,
                            'erro': erro
                        }
                else:
                    print(f"[SANKHYA SERVICE] Customer integration não disponível")
                    return {
                        'sucesso': False,
                        'erro': 'Cliente não encontrado e customer integration não disponível'
                    }
        
        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro no _processar_cliente_completo: {e}")
            import traceback
            traceback.print_exc()
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def _extrair_documento_billing(self, billing, dados_completos):
        """
        Extrai documento (CPF/CNPJ) do billing de forma inteligente
        
        Args:
            billing: Dicionário billing do WooCommerce
            dados_completos: Payload completo do pedido
            
        Returns:
            String com documento limpo (apenas números) ou None
        """
        documento = None
        
        # Campos possíveis onde o documento pode estar
        campos_billing = ['cpf', 'cnpj', 'document', 'tax_id', 'number', 'persontype']
        
        print(f"[SANKHYA SERVICE] Buscando documento (CPF/CNPJ)...")
        
        # 1. Buscar em billing direto
        if billing:
            for campo in campos_billing:
                valor = billing.get(campo, '').strip()
                if valor and valor not in ['1', '2', 'CPF', 'CNPJ']:  # Ignora valores de tipo
                    documento = valor
                    print(f"[SANKHYA SERVICE] Documento encontrado em billing.{campo}: {documento}")
                    break
        
        # 2. Buscar em meta_data
        if not documento:
            metadata = dados_completos.get('meta_data', [])
            for meta in metadata:
                key = meta.get('key', '')
                if key in campos_billing or key.startswith('_billing_'):
                    value = str(meta.get('value', '')).strip()
                    if value and value not in ['1', '2', 'CPF', 'CNPJ'] and len(value) >= 11:
                        documento = value
                        print(f"[SANKHYA SERVICE] Documento encontrado em meta_data.{key}: {documento}")
                        break
        
        # 3. Buscar no nível raiz dos dados completos
        if not documento:
            for campo in campos_billing:
                valor = dados_completos.get(campo, '').strip()
                if valor and valor not in ['1', '2', 'CPF', 'CNPJ']:
                    documento = valor
                    print(f"[SANKHYA SERVICE] Documento encontrado no nível raiz.{campo}: {documento}")
                    break
        
        # 4. Limpeza e validação
        if documento:
            # Remove formatação (pontos, hífens, barras)
            documento_limpo = re.sub(r'\D', '', str(documento))
            
            # Validação: CPF tem 11 dígitos, CNPJ tem 14
            if len(documento_limpo) in [11, 14]:
                print(f"[SANKHYA SERVICE] Documento limpo e válido: {documento_limpo} ({len(documento_limpo)} dígitos)")
                return documento_limpo
            else:
                print(f"[SANKHYA SERVICE] Documento com tamanho inválido: {documento_limpo} ({len(documento_limpo)} dígitos)")
                return None
        
        print(f"[SANKHYA SERVICE] Nenhum documento encontrado")
        return None
    
    def _processar_transportadora(self, payload):
        """
        Processa informações de transportadora do pedido WooCommerce
        
        Args:
            payload: Dados completos do pedido
            
        Returns:
            Dicionário com informações da transportadora:
            - transportadora_encontrada: bool
            - codparc_transportadora: int (se encontrada)
            - nome_transportadora: str (se encontrada)
            - valor_frete: float
            - erro: str (se houver erro)
        """
        try:
            shipping_lines = payload.get('shipping_lines', [])
            
            if not shipping_lines or len(shipping_lines) == 0:
                print(f"[SANKHYA SERVICE] Pedido sem informações de frete")
                return {
                    'transportadora_encontrada': False,
                    'erro': 'Nenhuma informação de frete encontrada',
                    'valor_frete': 0
                }
            
            # Pega a primeira linha de frete
            frete_info = shipping_lines[0]
            metodo_envio = frete_info.get('method_title', '')
            valor_frete = float(frete_info.get('total', 0))
            
            print(f"[SANKHYA SERVICE] Método de envio: {metodo_envio}")
            print(f"[SANKHYA SERVICE] Valor do frete: R$ {valor_frete:.2f}")
            
            try:
                # Processar shipping do WooCommerce
                transportadora = self.transportadoras.processar_shipping_woocommerce(shipping_lines)
                
                if transportadora:
                    codparc = transportadora.get('CODPARC')
                    nome = transportadora.get('NOMEPARC', '')
                    
                    print(f"[SANKHYA SERVICE] Transportadora encontrada:")
                    print(f"[SANKHYA SERVICE]   CODPARC: {codparc}")
                    print(f"[SANKHYA SERVICE]   Nome: {nome}")
                    
                    return {
                        'transportadora_encontrada': True,
                        'codparc_transportadora': codparc,
                        'nome_transportadora': nome,
                        'valor_frete': valor_frete
                    }
                else:
                    print(f"[SANKHYA SERVICE] Nenhuma transportadora mapeada para: {metodo_envio}")
                    return {
                        'transportadora_encontrada': False,
                        'motivo': f'Método de envio não mapeado: {metodo_envio}',
                        'valor_frete': valor_frete
                    }
            
            except Exception as e_transp:
                print(f"[SANKHYA SERVICE] Erro ao processar transportadora: {e_transp}")
                return {
                    'transportadora_encontrada': False,
                    'erro': str(e_transp),
                    'valor_frete': valor_frete
                }
        
        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro ao processar transportadora: {e}")
            return {
                'transportadora_encontrada': False,
                'erro': str(e),
                'valor_frete': 0
            }
    
    # MÉTODOS PÚBLICOS ADICIONAIS
    
    def processar_pedido_completo(self, dados_pedido):
        """
        Método público para processar pedido completo
        
        Args:
            dados_pedido: Dados do pedido do WooCommerce
            
        Returns:
            Resultado do processamento
        """
        return self._processar_pedido_criado(dados_pedido)
    
    def diagnosticar_pedido(self, produtos_wc):
        """
        Método público para diagnóstico de produtos
        
        Args:
            produtos_wc: Lista de produtos do WooCommerce
            
        Returns:
            Resultado do diagnóstico
        """
        return self._diagnosticar_pedido_completo(produtos_wc)
    
    def consultar_parceiro(self, documento):
        """
        Consulta parceiro por documento (CPF/CNPJ)
        
        Args:
            documento: CPF ou CNPJ (com ou sem formatação)
            
        Returns:
            Dados do parceiro ou None
        """
        try:
            documento_limpo = re.sub(r'\D', '', str(documento))
            return self.parceiros.consultar_por_documento(documento_limpo)
        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro ao consultar parceiro: {e}")
            return None
    
    def processar_cliente_completo(self, dados_cliente):
        """
        Método público para processar cliente
        
        Args:
            dados_cliente: Dados do cliente do WooCommerce
            
        Returns:
            Resultado do processamento
        """
        try:
            # Formatar payload se necessário
            payload_formatado = {
                'customer_id': dados_cliente.get('id', 0),
                'billing': dados_cliente.get('billing', dados_cliente)
            }
            
            return self._processar_cliente_completo(payload_formatado)
        
        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro no método público processar_cliente_completo: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def normalizar_campos_sankhya(self, item_dict):
        """
        Converte campos para o padrão esperado pelo Sankhya (maiúsculo)
        
        Args:
            item_dict: Dicionário com campos em minúsculo
            
        Returns:
            Dicionário com campos em MAIÚSCULO
        """
        mapeamento = {
            'codprod': 'CODPROD',
            'qtdneg': 'QTDNEG',
            'codlocalorig': 'CODLOCALORIG',
            'codvol': 'CODVOL',
            'vlrunit': 'VLRUNIT',
            'vlrtot': 'VLRTOT',
            'vlrdesc': 'VLRDESC',
            'percdesc': 'PERCDESC'
        }
        
        item_normalizado = {}
        for campo_original, valor in item_dict.items():
            campo_sankhya = mapeamento.get(campo_original, campo_original.upper())
            item_normalizado[campo_sankhya] = valor
        
        return item_normalizado

    def _salvar_nunota_woocommerce(self, pedido_id, nunota):
        """
        Salva o NUNOTA único no pedido do WooCommerce
        """
        try:
            from services.woocommerce.service import WooCommerceService
            
            woo_service = WooCommerceService()
            
            # Preparar meta_data
            meta_data = [
                {
                    "key": "Sankhya_NUNOTA",
                    "value": str(nunota)
                },
                {
                    "key": "_sankhya_nunota",
                    "value": str(nunota)
                }
            ]
            
            # Atualizar pedido
            update_data = {
                "meta_data": meta_data
            }
            
            resultado = woo_service.update_order(pedido_id, update_data)
            
            if resultado:
                print(f"[SANKHYA SERVICE] NUNOTA {nunota} salvo no pedido WooCommerce {pedido_id}")
                return True
            else:
                print(f"[SANKHYA SERVICE] Falha ao salvar NUNOTA no WooCommerce")
                return False
                
        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro ao salvar NUNOTA: {e}")
            return False

    def _salvar_multiplos_nunotas_woocommerce(self, pedido_id, nunotas_lista):
        """
        Salva múltiplos NUNOTAs no WooCommerce
        """
        try:
            from services.woocommerce.service import WooCommerceService
            
            woo_service = WooCommerceService()
            
            # Preparar meta_data
            meta_data = []
            
            # 1. Salvar lista completa como JSON
            import json
            meta_data.append({
                "key": "_sankhya_nunotas",
                "value": json.dumps(nunotas_lista)
            })
            
            # 2. Salvar NUNOTAs individuais
            for i, nunota_info in enumerate(nunotas_lista):
                nunota = nunota_info.get('nunota')
                estoque = nunota_info.get('estoque')
                codtipoper = nunota_info.get('codtipoper')
                
                meta_data.append({
                    "key": f"_sankhya_nunota_{i+1}",
                    "value": str(nunota)
                })
                
                meta_data.append({
                    "key": f"_sankhya_estoque_{i+1}",
                    "value": str(estoque)
                })
                
                meta_data.append({
                    "key": f"_sankhya_codtipoper_{i+1}",
                    "value": str(codtipoper)
                })
                
                print(f"[SANKHYA SERVICE] NUNOTA {i+1}: {nunota} (Estoque: {estoque}, CODTIPOPER: {codtipoper})")
            
            # 3. Salvar contador
            meta_data.append({
                "key": "_sankhya_nunotas_count",
                "value": str(len(nunotas_lista))
            })
            
            # Atualizar pedido
            update_data = {
                "meta_data": meta_data
            }
            
            resultado = woo_service.update_order(pedido_id, update_data)
            
            if resultado:
                print(f"[SANKHYA SERVICE] {len(nunotas_lista)} NUNOTAs salvos no pedido WooCommerce {pedido_id}")
                return True
            else:
                print(f"[SANKHYA SERVICE] Falha ao salvar NUNOTAs no WooCommerce")
                return False
                
        except Exception as e:
            print(f"[SANKHYA SERVICE] Erro ao salvar múltiplos NUNOTAs: {e}")
            return False


# CONTEXT MANAGER - CORRIGIDO

class SankhyaServiceContext:
    """
    Context manager para SankhyaService com autenticação automática
    
    Uso:
        with SankhyaServiceContext() as service:
            nunota = service.obter_nunota_por_id_woocommerce(14158)
            xml = service._obter_xml_nfe_por_nunota(nunota)
    """
    
    def __init__(self):
        """Inicializa o context manager"""
        self.auth = None
        self.service = None
        self.token = None
    
    def __enter__(self) -> SankhyaService:
        """
        Entra no contexto: autentica e cria serviço
        
        Returns:
            Instncia de SankhyaService autenticada
        """
        try:
            print(f"[SANKHYA SERVICE CONTEXT] Iniciando autenticação...")
            
            # CORREÇÃO 7: SankhyaAuth já foi importado no topo
            self.auth = SankhyaAuth()
            self.token = self.auth.login()
            
            if not self.token:
                raise Exception("Falha na autenticação com Sankhya")
            
            print(f"[SANKHYA SERVICE CONTEXT] Autenticação realizada com sucesso")
            
            # Cria instncia do serviço com token
            self.service = SankhyaService(self.token)
            
            print(f"[SANKHYA SERVICE CONTEXT] Serviços Sankhya inicializados")
            return self.service
            
        except Exception as e:
            print(f"[SANKHYA SERVICE CONTEXT] Erro na inicialização: {e}")
            # Se deu erro, tenta fazer logout se tiver token
            if self.auth and self.token:
                try:
                    self.auth.logout()
                except:
                    pass
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Sai do contexto: faz logout
        
        Args:
            exc_type: Tipo da exceção (se houver)
            exc_val: Valor da exceção (se houver)
            exc_tb: Traceback da exceção (se houver)
            
        Returns:
            bool: False para re-levantar exceção, True para suprimir
        """
        try:
            if self.auth and self.token:
                print(f"[SANKHYA SERVICE CONTEXT] Realizando logout...")
                self.auth.logout()
                print(f"[SANKHYA SERVICE CONTEXT] Logout realizado com sucesso")
        except Exception as e:
            print(f"[SANKHYA SERVICE CONTEXT] Erro no logout: {e}")
        finally:
            # Limpa referências
            self.service = None
            self.token = None
            self.auth = None
        
        # Se houve exceção, re-levanta
        if exc_type:
            print(f"[SANKHYA SERVICE CONTEXT] Erro durante execução: {exc_val}")
            return False
        
        return True

# FUNÇÕES DE CONVENIÊNCIA

def obter_nfe_por_pedido_woocommerce(id_woocommerce: int) -> Dict[str, Any]:
    """
    Função de conveniência para obter NFe completa de um pedido
    
    Args:
        id_woocommerce: ID do pedido no WooCommerce
        
    Returns:
        Dicionário com:
        - success: bool
        - nunota: int (se sucesso)
        - xml: str (se sucesso)
        - pdf: bytes (se sucesso)
        - error: str (se falha)
    """
    try:
        with SankhyaService.with_auth() as service:
            # Buscar NUNOTA
            nunota = service.obter_nunota_por_id_woocommerce(id_woocommerce)
            
            if not nunota:
                return {
                    'success': False,
                    'error': 'NUNOTA não encontrado (NFe não emitida?)'
                }
            
            # Buscar XML
            xml = service._obter_xml_nfe_por_nunota(nunota)
            
            # Gerar PDF
            pdf = service.obter_danfe_pdf(nunota)
            
            return {
                'success': True,
                'nunota': nunota,
                'xml': xml,
                'pdf': pdf
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# Exportações
__all__ = [
    'SankhyaService',
    'SankhyaServiceContext',
    'obter_nfe_por_pedido_woocommerce'
]


# MÉTODOS ADICIONAIS DE UTILIDADE

def obter_status_nfe(nunota: int) -> Dict[str, Any]:
    """
    Consulta o status atual de uma NFe no Sankhya
    
    Args:
        nunota: Número único da nota fiscal
        
    Returns:
        Dicionário com informações da NFe:
        - success: bool
        - status: str (A=Aprovada, D=Denegada, etc)
        - numero: str (número da nota)
        - chave: str (chave de acesso)
        - data_emissao: str
        - valor: float
        - error: str (se falha)
    """
    try:
        with SankhyaService.with_auth() as service:
            client = SankhyaClient(service.token)
            
            # Buscar informações da NFe
            criteria = {
                "expression": {"$": "this.NUNOTA = ?"},
                "parameter": [{"$": str(nunota), "type": "I"}]
            }
            
            resultado = client.load_records(
                entity="CabecalhoNota",
                fields="NUNOTA,NUMNOTA,CHAVENFE,STATUSNFE,DTFATUR,VLRNOTA,SERIENOTA",
                criteria=criteria,
                limit=1
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total == 0:
                return {
                    'success': False,
                    'error': f'NFe com NUNOTA {nunota} não encontrada'
                }
            
            # Extrair dados
            entity = entities.get("entity")
            if isinstance(entity, list):
                entity = entity[0]
            
            status_map = {
                'A': 'Aprovada',
                'D': 'Denegada',
                'E': 'Aguardando Autorização',
                'P': 'Pendente',
                'R': 'Aguardando Correção',
                'C': 'Cancelada'
            }
            
            status_code = entity.get('f3', {}).get('$', '')
            
            return {
                'success': True,
                'nunota': int(entity.get('f0', {}).get('$', 0)),
                'numero': entity.get('f1', {}).get('$', ''),
                'chave': entity.get('f2', {}).get('$', ''),
                'status_code': status_code,
                'status': status_map.get(status_code, 'Desconhecido'),
                'data_emissao': entity.get('f4', {}).get('$', ''),
                'valor': float(entity.get('f5', {}).get('$', 0)),
                'serie': entity.get('f6', {}).get('$', '')
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def validar_documento(documento: str) -> Dict[str, Any]:
    """
    Valida CPF ou CNPJ
    
    Args:
        documento: String com CPF ou CNPJ (com ou sem formatação)
        
    Returns:
        Dicionário com:
        - valido: bool
        - tipo: 'CPF' ou 'CNPJ'
        - documento_limpo: str (apenas números)
        - erro: str (se inválido)
    """
    try:
        # Remove formatação
        doc_limpo = re.sub(r'\D', '', str(documento))
        
        # Verifica tamanho
        if len(doc_limpo) == 11:
            # CPF
            # Validação simples de tamanho
            if doc_limpo == '00000000000' or doc_limpo == '11111111111':
                return {
                    'valido': False,
                    'erro': 'CPF inválido (sequência)'
                }
            
            return {
                'valido': True,
                'tipo': 'CPF',
                'documento_limpo': doc_limpo
            }
        
        elif len(doc_limpo) == 14:
            # CNPJ
            if doc_limpo == '00000000000000':
                return {
                    'valido': False,
                    'erro': 'CNPJ inválido (zeros)'
                }
            
            return {
                'valido': True,
                'tipo': 'CNPJ',
                'documento_limpo': doc_limpo
            }
        
        else:
            return {
                'valido': False,
                'erro': f'Documento com tamanho inválido: {len(doc_limpo)} dígitos'
            }
    
    except Exception as e:
        return {
            'valido': False,
            'erro': str(e)
        }


def formatar_documento(documento: str) -> str:
    """
    Formata CPF ou CNPJ
    
    Args:
        documento: String com números do documento
        
    Returns:
        String formatada (###.###.###-## ou ##.###.###/####-##)
    """
    doc_limpo = re.sub(r'\D', '', str(documento))
    
    if len(doc_limpo) == 11:
        # CPF: ###.###.###-##
        return f"{doc_limpo[:3]}.{doc_limpo[3:6]}.{doc_limpo[6:9]}-{doc_limpo[9:]}"
    
    elif len(doc_limpo) == 14:
        # CNPJ: ##.###.###/####-##
        return f"{doc_limpo[:2]}.{doc_limpo[2:5]}.{doc_limpo[5:8]}/{doc_limpo[8:12]}-{doc_limpo[12:]}"
    
    else:
        return documento


def gerar_relatorio_integracao(data_inicio: str, data_fim: str) -> Dict[str, Any]:
    """
    Gera relatório de integrações realizadas em um período
    
    Args:
        data_inicio: Data inicial (YYYY-MM-DD)
        data_fim: Data final (YYYY-MM-DD)
        
    Returns:
        Dicionário com estatísticas das integrações
    """
    try:
        with SankhyaService.with_auth() as service:
            client = SankhyaClient(service.token)
            
            # Converter datas para o formato Sankhya (DD/MM/YYYY)
            dt_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            dt_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
            
            dt_inicio_sankhya = dt_inicio_obj.strftime('%d/%m/%Y')
            dt_fim_sankhya = dt_fim_obj.strftime('%d/%m/%Y')
            
            # Buscar notas do período com ID WooCommerce
            criteria = {
                "expression": {
                    "$": "this.DTNEG BETWEEN ? AND ? AND this.AD_IDWOOCOMMERCE IS NOT NULL"
                },
                "parameter": [
                    {"$": dt_inicio_sankhya, "type": "D"},
                    {"$": dt_fim_sankhya, "type": "D"}
                ]
            }
            
            resultado = client.load_records(
                entity="CabecalhoNota",
                fields="NUNOTA,NUMNOTA,DTNEG,VLRNOTA,AD_IDWOOCOMMERCE",
                criteria=criteria,
                limit=1000
            )
            
            entities = resultado.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total == 0:
                return {
                    'success': True,
                    'periodo': f"{data_inicio} a {data_fim}",
                    'total_pedidos': 0,
                    'valor_total': 0,
                    'pedidos': []
                }
            
            # Processar resultados
            entity_list = entities.get("entity", [])
            if not isinstance(entity_list, list):
                entity_list = [entity_list]
            
            pedidos = []
            valor_total = 0
            
            for entity in entity_list:
                vlrnota = float(entity.get('f3', {}).get('$', 0))
                valor_total += vlrnota
                
                pedidos.append({
                    'nunota': int(entity.get('f0', {}).get('$', 0)),
                    'numnota': entity.get('f1', {}).get('$', ''),
                    'data': entity.get('f2', {}).get('$', ''),
                    'valor': vlrnota,
                    'id_woocommerce': entity.get('f4', {}).get('$', '')
                })
            
            return {
                'success': True,
                'periodo': f"{data_inicio} a {data_fim}",
                'total_pedidos': total,
                'valor_total': valor_total,
                'pedidos': pedidos
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# CLASSES AUXILIARES

class SankhyaServiceException(Exception):
    """Exceção customizada para erros do SankhyaService"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        """
        Inicializa a exceção
        
        Args:
            message: Mensagem de erro
            details: Detalhes adicionais do erro
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a exceção para dicionário
        
        Returns:
            Dicionário com erro e detalhes
        """
        return {
            'error': self.message,
            'details': self.details
        }


class SankhyaServiceLogger:
    """Logger customizado para SankhyaService"""
    
    def __init__(self, service_name: str = "SANKHYA SERVICE"):
        """
        Inicializa o logger
        
        Args:
            service_name: Nome do serviço para os logs
        """
        self.service_name = service_name
        self.logs = []
    
    def log(self, level: str, message: str, **kwargs):
        """
        Adiciona um log
        
        Args:
            level: Nível do log (INFO, WARNING, ERROR, etc)
            message: Mensagem do log
            **kwargs: Dados adicionais
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'service': self.service_name,
            'message': message,
            **kwargs
        }
        
        self.logs.append(log_entry)
        
        # Print também
        emoji_map = {
            'INFO': 'ℹ️',
            'SUCCESS': '',
            'WARNING': '',
            'ERROR': '❌',
            'DEBUG': '🔍'
        }
        
        emoji = emoji_map.get(level, '📝')
        print(f"[{self.service_name}] {emoji} {message}")
    
    def info(self, message: str, **kwargs):
        """Log de informação"""
        self.log('INFO', message, **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log de sucesso"""
        self.log('SUCCESS', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log de aviso"""
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log de erro"""
        self.log('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log de debug"""
        self.log('DEBUG', message, **kwargs)
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os logs
        
        Returns:
            Lista de dicionários com os logs
        """
        return self.logs
    
    def clear_logs(self):
        """Limpa todos os logs"""
        self.logs = []
    
    def export_logs(self, filepath: str):
        """
        Exporta logs para arquivo JSON
        
        Args:
            filepath: Caminho do arquivo
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)


# UTILITÁRIOS DE CONVERSÃO

def converter_data_sankhya_para_iso(data_sankhya: str) -> str:
    """
    Converte data do formato Sankhya (DD/MM/YYYY) para ISO (YYYY-MM-DD)
    
    Args:
        data_sankhya: Data no formato DD/MM/YYYY
        
    Returns:
        Data no formato YYYY-MM-DD
    """
    try:
        dt = datetime.strptime(data_sankhya.split()[0], '%d/%m/%Y')
        return dt.strftime('%Y-%m-%d')
    except:
        return data_sankhya


def converter_data_iso_para_sankhya(data_iso: str) -> str:
    """
    Converte data do formato ISO (YYYY-MM-DD) para Sankhya (DD/MM/YYYY)
    
    Args:
        data_iso: Data no formato YYYY-MM-DD
        
    Returns:
        Data no formato DD/MM/YYYY
    """
    try:
        dt = datetime.strptime(data_iso, '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except:
        return data_iso


def normalizar_valor_monetario(valor: Any) -> float:
    """
    Normaliza valor monetário para float
    
    Args:
        valor: Valor em string, int ou float
        
    Returns:
        Float com o valor
    """
    try:
        # Remove símbolos monetários e converte vírgulas
        valor_str = str(valor).replace('R$', '').replace('$', '').strip()
        valor_str = valor_str.replace('.', '').replace(',', '.')
        return float(valor_str)
    except:
        return 0.0


# CONSTANTES E CONFIGURAÇÕES

# Status possíveis de NFe
NFE_STATUS = {
    'A': 'Aprovada',
    'D': 'Denegada',
    'E': 'Aguardando Autorização',
    'P': 'Pendente',
    'R': 'Aguardando Correção',
    'C': 'Cancelada',
    'I': 'Inutilizada'
}

# Status de pedidos WooCommerce mapeados
WOOCOMMERCE_STATUS_MAP = {
    'pending': {'acao': 'monitorar', 'descricao': 'Aguardando pagamento'},
    'processing': {'acao': 'processar', 'descricao': 'Processando'},
    'on-hold': {'acao': 'monitorar', 'descricao': 'Aguardando'},
    'completed': {'acao': 'concluido', 'descricao': 'Concluído'},
    'cancelled': {'acao': 'cancelar', 'descricao': 'Cancelado'},
    'refunded': {'acao': 'estornar', 'descricao': 'Reembolsado'},
    'failed': {'acao': 'falhar', 'descricao': 'Falhou'}
}

# Campos obrigatórios para criar pedido
CAMPOS_OBRIGATORIOS_PEDIDO = [
    'id',
    'billing',
    'line_items'
]

# Campos obrigatórios no billing
CAMPOS_OBRIGATORIOS_BILLING = [
    'first_name',
    'last_name',
    'email'
]

# Timeout padrão para requisições (segundos)
DEFAULT_TIMEOUT = 30

# Número máximo de tentativas em caso de erro
MAX_RETRIES = 3

# Versão do serviço
SERVICE_VERSION = '2.6.0'


# INFORMAÇÕES DO MÓDULO

__version__ = SERVICE_VERSION
__author__ = 'Suedes Carletti'
__description__ = 'Serviço de integração completo entre WooCommerce e Sankhya ERP'
__all__ = [
    # Classes principais
    'SankhyaService',
    'SankhyaServiceContext',
    'SankhyaServiceException',
    'SankhyaServiceLogger',
    
    # Funções utilitárias
    'obter_nfe_por_pedido_woocommerce',
    'obter_status_nfe',
    'validar_documento',
    'formatar_documento',
    'gerar_relatorio_integracao',
    'converter_data_sankhya_para_iso',
    'converter_data_iso_para_sankhya',
    'normalizar_valor_monetario',
    
    # Constantes
    'NFE_STATUS',
    'WOOCOMMERCE_STATUS_MAP',
    'SERVICE_VERSION'
]
