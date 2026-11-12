from .base import SankhyaClient

class EstoqueService(SankhyaClient):
    """
    Serviço para consulta e gestão de estoque
    """
    
    def __init__(self, token=None):
        super().__init__(token)
        self.cache_locais_produto = {}  # Cache para performance

    def consultar_estoque_produto(self, codprod, somente_venda=True):
        """
        Consulta estoque do produto e retorna locais disponíveis
        
        Args:
            codprod: Código do produto
            somente_venda: Se True, filtra apenas locais com final "01"
        
        Returns:
            list: Lista de dicionários com informações do estoque
        """
        try:
            # Verifica cache
            cache_key = f"{codprod}_{somente_venda}"
            if cache_key in self.cache_locais_produto:
                print(f"[ESTOQUE] Cache hit para produto {codprod}")
                return self.cache_locais_produto[cache_key]

            print(f"[ESTOQUE] Consultando estoque do produto: {codprod}")
            
            # Monta critério de busca com LIKE para locais terminados em "01"
            if somente_venda:
                # Filtra locais que terminam em "01" usando LIKE
                expression = "this.CODPROD = ? AND this.ATIVO = 'S' AND this.ESTOQUE > 0 AND this.CODLOCAL LIKE '%01'"
                parameters = [{"$": str(codprod), "type": "I"}]
            else:
                # Busca todos os locais com estoque
                expression = "this.CODPROD = ? AND this.ATIVO = 'S' AND this.ESTOQUE > 0"
                parameters = [{"$": str(codprod), "type": "I"}]
            
            criteria = {
                "expression": {"$": expression},
                "parameter": parameters
            }
            
            # Consulta estoque
            result = self.load_records(
                entity="Estoque",
                fields="CODPROD,CODLOCAL,ESTOQUE,RESERVADO,ATIVO,CODEMP",
                criteria=criteria,
                limit=50
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total == 0:
                print(f"[ESTOQUE] Produto {codprod} não encontrado no estoque" + 
                      (" de venda (locais *01)" if somente_venda else ""))
                self.cache_locais_produto[cache_key] = []
                return []
            
            # Processa resultados
            entity_list = entities.get("entity", [])
            if not isinstance(entity_list, list):
                entity_list = [entity_list]
            
            estoques = []
            for entity in entity_list:
                estoque_info = {
                    'CODPROD': entity.get('f0', {}).get('$', ''),
                    'CODLOCAL': entity.get('f1', {}).get('$', ''),
                    'ESTOQUE': float(entity.get('f2', {}).get('$', '0')),
                    'RESERVADO': float(entity.get('f3', {}).get('$', '0')),
                    'ATIVO': entity.get('f4', {}).get('$', 'S'),
                    'CODEMP': entity.get('f5', {}).get('$', '')
                }
                
                # Validação adicional no lado Python para garantia
                if somente_venda and not self._is_local_venda(estoque_info['CODLOCAL']):
                    continue
                
                estoques.append(estoque_info)
            
            # Ordena por estoque disponível (maior primeiro)
            estoques.sort(key=lambda x: x['ESTOQUE'] - x['RESERVADO'], reverse=True)
            
            print(f"[ESTOQUE] Encontrados {len(estoques)} locais para produto {codprod}")
            for est in estoques[:3]:  # Mostra apenas os 3 primeiros
                disponivel = est['ESTOQUE'] - est['RESERVADO']
                print(f"[ESTOQUE]   Local {est['CODLOCAL']}: {disponivel:.2f} disponível")
            
            # Armazena no cache
            self.cache_locais_produto[cache_key] = estoques
            
            return estoques
            
        except Exception as e:
            print(f"[ESTOQUE] Erro ao consultar estoque do produto {codprod}: {e}")
            return []
    
    def _is_local_venda(self, codlocal):
        """
        Verifica se o local é para venda (centenas com final "01")
        """
        try:
            codlocal_str = str(codlocal)
            
            # Verifica se termina com "01"
            if not codlocal_str.endswith("01"):
                return False
            
            # Verifica se é centena (pelo menos 3 dígitos)
            if len(codlocal_str) < 3:
                return False
                
            # Verifica se todos os caracteres são dígitos
            if not codlocal_str.isdigit():
                return False
                
            return True
            
        except Exception:
            return False
    
    def obter_codlocalorig_produto(self, codprod):
        """
        Obtém o CODLOCALORIG mais adequado para um produto específico
        
        Returns:
            str: CODLOCALORIG do local com maior estoque disponível
        """
        print(f"[ESTOQUE] Buscando melhor local para produto {codprod}")
        
        # Primeiro tenta locais de venda (terminados em 01)
        estoques_venda = self.consultar_estoque_produto(codprod, somente_venda=True)
        
        if estoques_venda:
            melhor_local = estoques_venda[0]['CODLOCAL']
            disponivel = estoques_venda[0]['ESTOQUE'] - estoques_venda[0]['RESERVADO']
            print(f"[ESTOQUE] Produto {codprod} → Local venda {melhor_local} ({disponivel:.2f} disponível)")
            return melhor_local
        
        print(f"[ESTOQUE] Produto {codprod} sem estoque em locais de venda (*01)")
        
        # Se não há estoque em locais de venda, tenta qualquer local
        estoques_todos = self.consultar_estoque_produto(codprod, somente_venda=False)
        
        if estoques_todos:
            local_alternativo = estoques_todos[0]['CODLOCAL']
            disponivel = estoques_todos[0]['ESTOQUE'] - estoques_todos[0]['RESERVADO']
            print(f"[ESTOQUE] Usando local alternativo: {local_alternativo} ({disponivel:.2f} disponível)")
            return local_alternativo
        
        # Se não encontrou nenhum estoque, busca o primeiro local de venda disponível
        print(f"[ESTOQUE] Produto {codprod} sem estoque em nenhum local")
        primeiro_local_venda = self.obter_primeiro_local_venda_disponivel()
        
        if primeiro_local_venda:
            print(f"[ESTOQUE] Usando primeiro local de venda disponível: {primeiro_local_venda}")
            return primeiro_local_venda
        
        # Último recurso: retorna erro, não há local válido
        raise ValueError(f"Produto {codprod} não possui estoque e nenhum local de venda está disponível no sistema")
    
    def obter_primeiro_local_venda_disponivel(self):
        """
        Obtém o primeiro local de venda disponível no sistema
        """
        try:
            print(f"[ESTOQUE] Buscando primeiro local de venda disponível...")
            
            # Busca locais que terminam em "01" com qualquer produto
            criteria = {
                "expression": {"$": "this.ATIVO = 'S' AND CAST(this.CODLOCAL AS VARCHAR) LIKE '%01'"},
                "parameter": []
            }
            
            result = self.load_records(
                entity="Estoque",
                fields="CODLOCAL",
                criteria=criteria,
                limit=1
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            total = int(entities.get("total", "0"))
            
            if total > 0:
                entity_list = entities.get("entity", [])
                if not isinstance(entity_list, list):
                    entity_list = [entity_list]
                
                primeiro_local = entity_list[0].get('f0', {}).get('$', '')
                if primeiro_local and self._is_local_venda(primeiro_local):
                    print(f"[ESTOQUE] Primeiro local de venda encontrado: {primeiro_local}")
                    return primeiro_local
            
            print(f"[ESTOQUE] Nenhum local de venda (*01) encontrado no sistema")
            return None
            
        except Exception as e:
            print(f"[ESTOQUE] Erro ao buscar primeiro local de venda: {e}")
            return None
    
    def listar_locais_venda_disponiveis(self, limite=20):
        """
        Lista todos os locais de venda (final "01") que têm produtos
        """
        try:
            print(f"[ESTOQUE] Listando locais de venda disponíveis...")
            
            # Busca locais únicos terminados em "01" com estoque
            criteria = {
                "expression": {"$": "this.ATIVO = 'S' AND this.ESTOQUE > 0 AND CAST(this.CODLOCAL AS VARCHAR) LIKE '%01'"},
                "parameter": []
            }
            
            result = self.load_records(
                entity="Estoque",
                fields="CODLOCAL",
                criteria=criteria,
                limit=limite * 5  # Busca mais para filtrar únicos
            )
            
            entities = result.get("responseBody", {}).get("entities", {})
            entity_list = entities.get("entity", [])
            if not isinstance(entity_list, list):
                entity_list = [entity_list]
            
            # Extrai locais únicos
            locais_unicos = set()
            for entity in entity_list:
                codlocal = entity.get('f0', {}).get('$', '')
                if self._is_local_venda(codlocal):
                    locais_unicos.add(codlocal)
            
            locais_ordenados = sorted(list(locais_unicos))[:limite]
            
            print(f"[ESTOQUE] Encontrados {len(locais_ordenados)} locais de venda")
            if locais_ordenados:
                print(f"[ESTOQUE]   Locais: {', '.join(locais_ordenados)}")
            
            return locais_ordenados
            
        except Exception as e:
            print(f"[ESTOQUE] Erro ao listar locais de venda: {e}")
            return []
    
    def diagnosticar_produto_estoque(self, codprod):
        """
        Faz diagnóstico completo do estoque de um produto
        """
        try:
            print(f"[ESTOQUE] Diagnóstico completo do produto {codprod}")
            
            # Consulta locais de venda
            estoques_venda = self.consultar_estoque_produto(codprod, somente_venda=True)
            
            # Consulta todos os locais
            estoques_todos = self.consultar_estoque_produto(codprod, somente_venda=False)
            
            # Local recomendado
            try:
                local_recomendado = self.obter_codlocalorig_produto(codprod)
            except ValueError as e:
                local_recomendado = None
                erro_local = str(e)
            else:
                erro_local = None
            
            diagnostico = {
                'produto': codprod,
                'locais_venda': estoques_venda,
                'todos_locais': estoques_todos,
                'total_venda': len(estoques_venda),
                'total_geral': len(estoques_todos),
                'tem_estoque_venda': len(estoques_venda) > 0,
                'tem_estoque_geral': len(estoques_todos) > 0,
                'local_recomendado': local_recomendado,
                'erro_local': erro_local
            }
            
            # Logs do diagnóstico
            print(f"[ESTOQUE] Diagnóstico produto {codprod}:")
            print(f"[ESTOQUE]   Locais venda (*01): {diagnostico['total_venda']}")
            print(f"[ESTOQUE]   Todos os locais: {diagnostico['total_geral']}")
            print(f"[ESTOQUE]   Local recomendado: {diagnostico['local_recomendado']}")
            
            if erro_local:
                print(f"[ESTOQUE]   Erro: {erro_local}")
            
            return diagnostico
            
        except Exception as e:
            print(f"[ESTOQUE] Erro no diagnóstico do produto {codprod}: {e}")
            return {
                'produto': codprod,
                'erro': str(e),
                'locais_venda': [],
                'todos_locais': [],
                'total_venda': 0,
                'total_geral': 0,
                'tem_estoque_venda': False,
                'tem_estoque_geral': False,
                'local_recomendado': None,
                'erro_local': str(e)
            }
