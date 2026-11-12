import re
from .base import SankhyaClient
from .estoque import EstoqueService

class ProdutosService(SankhyaClient):
    """
    Serviço para consulta e mapeamento de produtos no Sankhya
    """
    
    def __init__(self, token=None):
        super().__init__(token)
        self.cache_produtos = {}
        self.estoque_service = EstoqueService(token)
    
    def mapear_produto(self, produto_wc):
            """
            ✅ CORRIGIDO: Mapeia produto do WooCommerce para o Sankhya usando múltiplas estratégias
            CORREÇÃO: Retorno padronizado compatível com SankhyaService
            """
            if not produto_wc:
                return None
            
            nome = produto_wc.get('name', '')
            sku = produto_wc.get('sku', '')
            product_id = produto_wc.get('product_id', 0)
            variation_id = produto_wc.get('variation_id', 0)
            
            print(f"[PRODUTOS] Mapeando produto:")
            print(f"[PRODUTOS]   Nome: {nome}")
            print(f"[PRODUTOS]   SKU: '{sku}'")
            print(f"[PRODUTOS]   Product ID: {product_id}")
            print(f"[PRODUTOS]   Variation ID: {variation_id}")
            
            # Preparar estratégias de busca
            estrategias = self._preparar_estrategias_busca(sku, product_id, variation_id)
            
            print(f"[PRODUTOS] Estratégias preparadas: {len(estrategias)}")
            
            # Tentar cada estratégia
            for estrategia in estrategias:
                print(f"[PRODUTOS] Tentando estratégia: {estrategia['nome']} ({estrategia['valor']})")
                resultado = self._executar_estrategia(estrategia)
                
                if resultado:
                    print(f"[PRODUTOS] Mapeamento bem-sucedido:")
                    print(f"[PRODUTOS]   Estratégia: {estrategia['nome']}")
                    print(f"[PRODUTOS]   Código WC: {estrategia['valor']} → Sankhya: {resultado['CODPROD']}")
                    print(f"[PRODUTOS]   Descrição: {resultado['DESCRPROD']}")
                    
                    # CORREÇÃO: Retorno padronizado para compatibilidade
                    return {
                        # Campos para SankhyaService (compatibilidade com versão antiga)
                        'CODPROD': resultado['CODPROD'],
                        'DESCRPROD': resultado['DESCRPROD'],
                        'CODLOCALORIG': resultado.get('CODLOCALORIG', 1),
                        'CODVOL': resultado.get('CODVOL', 'UN'),
                        
                        # Campos novos (estrutura melhorada)
                        'estrategia_usada': estrategia['nome'],
                        'codigo_wc': estrategia['valor'],
                        'codprod_sankhya': resultado['CODPROD'],
                        'descricao_sankhya': resultado['DESCRPROD'],
                        'produto_encontrado': True,
                        
                        # Dados completos do Sankhya
                        'dados_sankhya': resultado
                    }
            
            print(f"[PRODUTOS] Nenhuma estratégia funcionou para o produto")
            
            # CORREÇÃO: Retorno padronizado para falha
            return {
                'CODPROD': None,
                'produto_encontrado': False,
                'estrategia_usada': None,
                'codigo_wc': sku or str(product_id),
                'codprod_sankhya': None,
                'descricao_sankhya': None,
                'erro': 'Nenhuma estratégia de mapeamento funcionou'
            }
    
    def mapear_produto_com_estoque(self, produto_wc):
        """
        Mapeia produto do WooCommerce incluindo validação de estoque
        """
        produto_info = self.mapear_produto(produto_wc)
        
        if not produto_info:
            return None
        
        # Adiciona informação do local de origem baseado no estoque
        codprod = produto_info['codprod_sankhya']
        
        try:
            codlocalorig = self.estoque_service.obter_codlocalorig_produto(codprod)
            produto_info['codlocalorig_sugerido'] = codlocalorig
            produto_info['tem_estoque'] = True
            
            # Adiciona diagnóstico de estoque
            diagnostico = self.estoque_service.diagnosticar_produto_estoque(codprod)
            produto_info['diagnostico_estoque'] = diagnostico
            
        except ValueError as e:
            print(f"[PRODUTOS] Erro no estoque do produto {codprod}: {e}")
            produto_info['codlocalorig_sugerido'] = None
            produto_info['tem_estoque'] = False
            produto_info['erro_estoque'] = str(e)
        
        return produto_info
    
    def _preparar_estrategias_busca(self, sku, product_id, variation_id):
        """
        ✅ CORRIGIDO: Normaliza SKU para remover sufixos e busca por CODPROD
        """
        estrategias = []

        if sku and sku.strip():
            sku_original = sku.strip()
            print(f"[PRODUTOS] SKU original: '{sku_original}'")

            # NORMALIZAÇÃO SIMPLES: Remove sufixos comuns (-1, -2, etc.)
            sku_normalizado = self._normalizar_sku_simples(sku_original)
            print(f"[PRODUTOS] SKU normalizado: '{sku_normalizado}'")

            # ÚNICA ESTRATÉGIA: CODPROD direto com SKU normalizado
            if sku_normalizado and sku_normalizado.isdigit():
                estrategias.append({
                    'nome': 'codprod_direto',
                    'tipo': 'codprod',
                    'valor': sku_normalizado,
                    'campo_busca': 'CODPROD'
                })
                print(f"[PRODUTOS] Busca direta: CODPROD = {sku_normalizado}")
            else:
                print(f"[PRODUTOS] SKU '{sku_original}' não pôde ser normalizado para numérico")

        return estrategias

    def _normalizar_sku_simples(self, sku):
        """
        ✅ NOVA FUNÇÃO: Normalização simples para remover sufixos comuns
        """
        if not sku:
            return None

        sku_str = str(sku).strip()

        # Se já é numérico, retorna como está
        if sku_str.isdigit():
            return sku_str

        # Remove sufixos comuns de variação
        sufixos = ['-1', '-2', '-3', '-A', '-B', '-C', '_1', '_2', '_3']
        for sufixo in sufixos:
            if sku_str.endswith(sufixo):
                sku_limpo = sku_str[:-len(sufixo)]
                if sku_limpo and sku_limpo.isdigit():
                    print(f"[PRODUTOS] Removido sufixo: {sku_str} → {sku_limpo}")
                    return sku_limpo

        # Se não conseguiu normalizar, retorna None
        print(f"[PRODUTOS] Não foi possível normalizar: '{sku_str}'")
        return None

    def _executar_estrategia(self, estrategia):
        """
        Executa uma estratégia específica de busca
        """
        tipo = estrategia['tipo']
        valor = estrategia['valor']
        campo = estrategia['campo_busca']
        
        if tipo == 'sku':
            return self.consultar_produto_por_sku(valor)
        elif tipo == 'codprod':
            return self.consultar_produto_por_codigo(valor)
        
        return None
    
    def consultar_produto_por_sku(self, sku):
        """
        Consulta produto por SKU (campo REFERENCIA)
        """
        if not sku:
            print(f"[PRODUTOS] SKU está vazio")
            return None
            
        sku_str = str(sku).strip()
        
        if not sku_str:
            print(f"[PRODUTOS] SKU vazio após limpeza")
            return None
        
        print(f"[PRODUTOS] Consultando SKU: '{sku_str}'")
        
        # Verifica cache
        if sku_str in self.cache_produtos:
            print(f"[PRODUTOS] Cache hit: {sku_str}")
            return self.cache_produtos[sku_str]
        
        try:
            criteria = {
                "expression": {"$": "UPPER(this.REFERENCIA) = ?"},
                "parameter": [
                    {"$": sku_str.upper(), "type": "S"}
                ]
            }
            
            result = self.load_records(
                entity="Produto",
                fields="CODPROD,DESCRPROD,REFERENCIA,ATIVO",
                criteria=criteria,
                limit=1
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                produto = entity_list[0]
                produto_info = {
                    'CODPROD': produto.get('f0', {}).get('$', ''),
                    'DESCRPROD': produto.get('f1', {}).get('$', ''),
                    'REFERENCIA': produto.get('f2', {}).get('$', ''),
                    'ATIVO': produto.get('f3', {}).get('$', 'S')
                }
                
                print(f"[PRODUTOS] Encontrado: {produto_info['CODPROD']} - {produto_info['DESCRPROD']}")
                
                # Armazena no cache
                self.cache_produtos[sku_str] = produto_info
                
                return produto_info
            
            print(f"[PRODUTOS] SKU '{sku_str}' não encontrado")
            
            # Cache negativo
            self.cache_produtos[sku_str] = None
            
            return None
            
        except Exception as e:
            print(f"[PRODUTOS] Erro ao consultar SKU '{sku_str}': {e}")
            return None
    
    def normalizar_codigo(self, codigo):
        """
        Normaliza código removendo sufixos comuns de variação
        """
        if not codigo:
            return None
            
        codigo_str = str(codigo).strip()
        print(f"[PRODUTOS] Normalizando: '{codigo_str}'")
        
        # Se já é numérico, retorna como está
        if codigo_str.isdigit():
            print(f"[PRODUTOS] Já numérico: {codigo_str}")
            return codigo_str
        
        # ESTRATÉGIA 1: Remove sufixos conhecidos de variação
        sufixos_variacao = ['-1', '-2', '-3', '-A', '-B', '-C', '_1', '_2', '_3', '_A', '_B', '_C']
        for sufixo in sufixos_variacao:
            if codigo_str.endswith(sufixo):
                codigo_limpo = codigo_str[:-len(sufixo)]
                if codigo_limpo and codigo_limpo.isdigit():
                    print(f"[PRODUTOS] Removido sufixo de variação: {codigo_str} → {codigo_limpo}")
                    return codigo_limpo
        
        # ESTRATÉGIA 2: Separa por caracteres comuns e pega a primeira parte numérica
        separadores = ['-', '_', ' ', '.', '/', '\\', '|', ';', ':', '+', '=', '@', '#', '$', '%', '^', '&', '*', '(', ')', '[', ']', '{', '}', '<', '>', '?', '!', '~', '`', '"', "'", ',', ' ']
        for sep in separadores:
            if sep in codigo_str:
                partes = codigo_str.split(sep)
                primeira_parte = partes[0].strip()
                if primeira_parte and primeira_parte.isdigit():
                    print(f"[PRODUTOS] Extraído antes de '{sep}': {codigo_str} → {primeira_parte}")
                    return primeira_parte
        
        # ESTRATÉGIA 3: Remove todos os caracteres não numéricos
        codigo_numerico = re.sub(r'[^\d]', '', codigo_str)
        if codigo_numerico and codigo_numerico.isdigit():
            print(f"[PRODUTOS] Extraído numérico: {codigo_str} → {codigo_numerico}")
            return codigo_numerico
        
        print(f"[PRODUTOS] Não foi possível normalizar: '{codigo_str}'")
        return None
    
    def consultar_produto_por_codigo(self, codigo_produto):
        """
        Consulta produto por CODPROD com validação rigorosa
        """
        if not codigo_produto:
            print(f"[PRODUTOS] Código do produto está vazio")
            return None
            
        codigo_str = str(codigo_produto).strip()
        
        # Validação crítica: Deve ser numérico e não vazio
        if not codigo_str:
            print(f"[PRODUTOS] Código vazio após limpeza")
            return None
            
        if not codigo_str.isdigit():
            print(f"[PRODUTOS] Código não numérico ignorado: '{codigo_str}'")
            return None
            
        # Validação adicional: Deve ser um número válido
        try:
            codigo_int = int(codigo_str)
            if codigo_int <= 0:
                print(f"[PRODUTOS] Código deve ser maior que zero: {codigo_int}")
                return None
        except ValueError:
            print(f"[PRODUTOS] Erro ao converter para número: '{codigo_str}'")
            return None
        
        # Verifica cache
        if codigo_str in self.cache_produtos:
            print(f"[PRODUTOS] Cache hit: {codigo_str}")
            return self.cache_produtos[codigo_str]
        
        print(f"[PRODUTOS] Consultando CODPROD: {codigo_str}")
        
        try:
            criteria = {
                "expression": {"$": "this.CODPROD = ?"},
                "parameter": [
                    {"$": codigo_str, "type": "I"}
                ]
            }
            
            result = self.load_records(
                entity="Produto",
                fields="CODPROD,DESCRPROD,REFERENCIA,ATIVO",
                criteria=criteria,
                limit=1
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                produto = entity_list[0]
                produto_info = {
                    'CODPROD': produto.get('f0', {}).get('$', ''),
                    'DESCRPROD': produto.get('f1', {}).get('$', ''),
                    'REFERENCIA': produto.get('f2', {}).get('$', ''),
                    'ATIVO': produto.get('f3', {}).get('$', 'S')
                }
                
                print(f"[PRODUTOS] Encontrado: {produto_info['CODPROD']} - {produto_info['DESCRPROD']}")
                
                # Armazena no cache
                self.cache_produtos[codigo_str] = produto_info
                
                return produto_info
            
            print(f"[PRODUTOS] Produto {codigo_str} não encontrado")
            
            # Cache negativo
            self.cache_produtos[codigo_str] = None
            
            return None
            
        except Exception as e:
            print(f"[PRODUTOS] Erro ao consultar produto {codigo_str}: {e}")
            return None
    
    def processar_diagnostico_produtos(self, produtos_wc):
        """
        Processa diagnóstico de mapeamento para múltiplos produtos
        """
        print(f"[PRODUTOS] Criando relatório de mapeamento para {len(produtos_wc)} itens")
        
        relatorio = {
            'total_itens': len(produtos_wc),
            'sucessos': 0,
            'problemas': 0,
            'detalhes': []
        }
        
        for i, produto_wc in enumerate(produtos_wc, 1):
            print(f"[PRODUTOS] Analisando item {i}: {produto_wc.get('name', 'Sem nome')}")
            
            resultado = self.mapear_produto_com_estoque(produto_wc)
            
            item_relatorio = {
                'posicao': i,
                'nome_wc': produto_wc.get('name', ''),
                'sku_wc': produto_wc.get('sku', ''),
                'product_id_wc': produto_wc.get('product_id', 0),
                'mapeado': False,
                'codprod_sankhya': None,
                'descricao_sankhya': None,
                'codlocalorig': None,
                'tem_estoque': False,
                'estrategia_usada': None,
                'erro': None
            }
            
            if resultado:
                if resultado.get('produto_encontrado'):
                    item_relatorio.update({
                        'mapeado': True,
                        'codprod_sankhya': resultado['codprod_sankhya'],
                        'descricao_sankhya': resultado['descricao_sankhya'],
                        'codlocalorig': resultado.get('codlocalorig_sugerido'),
                        'tem_estoque': resultado.get('tem_estoque', False),
                        'estrategia_usada': resultado['estrategia_usada']
                    })
                    
                    if resultado.get('erro_estoque'):
                        item_relatorio['erro'] = resultado['erro_estoque']
                        relatorio['problemas'] += 1
                    else:
                        relatorio['sucessos'] += 1
                        
                    print(f"[PRODUTOS] Mapeamento bem-sucedido:")
                    print(f"[PRODUTOS]   Estratégia: {resultado['estrategia_usada']}")
                    print(f"[PRODUTOS]   Código WC: {resultado['codigo_wc']} → Sankhya: {resultado['codprod_sankhya']}")
                    print(f"[PRODUTOS]   Descrição: {resultado['descricao_sankhya']}")
                else:
                    item_relatorio['erro'] = "Produto não encontrado no Sankhya"
                    relatorio['problemas'] += 1
            else:
                item_relatorio['erro'] = "Falha no mapeamento"
                relatorio['problemas'] += 1
            
            relatorio['detalhes'].append(item_relatorio)
        
        print(f"[PRODUTOS] Relatório concluído:")
        print(f"[PRODUTOS]   Sucessos: {relatorio['sucessos']}")
        print(f"[PRODUTOS]   Problemas: {relatorio['problemas']}")
        
        return relatorio
    
    def limpar_cache(self):
        """
        Limpa cache de produtos
        """
        tamanho_anterior = len(self.cache_produtos)
        self.cache_produtos.clear()
        print(f"[PRODUTOS] Cache limpo: {tamanho_anterior} itens removidos")
