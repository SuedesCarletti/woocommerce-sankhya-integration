"""
Configurações CORRIGIDAS para integração WooCommerce-Sankhya
CORREÇÃO: Cache de configuração para evitar logs repetitivos
"""

import os
from dotenv import load_dotenv

# Cache global para evitar múltiplas inicializações
_config_cache = None
_config_loaded = False

def load_config(app=None, force_reload=False):
    """
    Carrega configurações centralizadas do ambiente
    CORRIGIDO: Com cache para evitar logs repetitivos
    """
    global _config_cache, _config_loaded
    
    # Se já foi carregado e não é reload forçado, retorna cache
    if _config_loaded and not force_reload and _config_cache is not None:
        if app and _config_cache:
            app.config.update(_config_cache)
        return _config_cache
    
    load_dotenv()
    
    # Determina ambiente
    usar_ambiente = os.getenv("USAR_AMBIENTE", "sandbox").lower()
    
    config = {
        # Webhook
        'WEBHOOK_SECRET': os.getenv("WEBHOOK_SECRET"),
        
        # WooCommerce
        'WC_URL': os.getenv("WC_URL"),
        'WC_KEY': os.getenv("WC_KEY"),
        'WC_SECRET': os.getenv("WC_SECRET"),
        'WC_WEBHOOK_SECRET': os.getenv("WC_WEBHOOK_SECRET"),
        
        # Sankhya - Ambiente dinâmico
        'USAR_AMBIENTE': usar_ambiente,
        'SANKHYA_USERNAME': os.getenv("SANKHYA_USERNAME"),
        'SANKHYA_PASSWORD': os.getenv("SANKHYA_PASSWORD"),
        
        # Configurações padrão do Sankhya
        'SANKHYA_CODLOCALORIG': os.getenv('SANKHYA_CODLOCALORIG', '1'),
        'SANKHYA_CODTIPOPER': os.getenv('SANKHYA_CODTIPOPER', '2000'),
        'SANKHYA_CODTIPVENDA': os.getenv('SANKHYA_CODTIPVENDA', '12'),
        'SANKHYA_CODVEND': os.getenv('SANKHYA_CODVEND', '0'),
        'SANKHYA_CODEMP': os.getenv('SANKHYA_CODEMP', '1'),
        'SANKHYA_CODNAT': os.getenv('SANKHYA_CODNAT', '1'),
        
        # Configurações para mapeamento de produtos
        'PRODUTOS_CACHE_TAMANHO': int(os.getenv('PRODUTOS_CACHE_TAMANHO', '1000')),
        'PRODUTOS_NORMALIZAR_SKUS': os.getenv('PRODUTOS_NORMALIZAR_SKUS', 'True').lower() == 'true',
        'PRODUTOS_PERMITIR_PROCESSAMENTO_PARCIAL': os.getenv('PRODUTOS_PERMITIR_PROCESSAMENTO_PARCIAL', 'True').lower() == 'true',
        
        # Configurações para transportadoras
        'TRANSPORTADORAS_USAR_PADRAO': os.getenv('TRANSPORTADORAS_USAR_PADRAO', 'True').lower() == 'true',
        'TRANSPORTADORAS_CODPARC_PADRAO': os.getenv('TRANSPORTADORAS_CODPARC_PADRAO', ''),
        
        # Configurações para pedidos
        'PEDIDOS_INFORMAR_PRECO': os.getenv('PEDIDOS_INFORMAR_PRECO', 'True').lower() == 'true',
        'PEDIDOS_TIPMOV_PADRAO': os.getenv('PEDIDOS_TIPMOV_PADRAO', 'P'),
        'PEDIDOS_INCLUIR_OBSERVACOES_WOO': os.getenv('PEDIDOS_INCLUIR_OBSERVACOES_WOO', 'True').lower() == 'true',
        
        # Configurações de segurança e validação
        'WEBHOOK_ALLOWED_IPS': os.getenv('WEBHOOK_ALLOWED_IPS', ''),
        'WEBHOOK_RATE_LIMIT': int(os.getenv('WEBHOOK_RATE_LIMIT', '100')),
        'VALIDAR_HMAC_SIGNATURE': os.getenv('VALIDAR_HMAC_SIGNATURE', 'False').lower() == 'true',
        
        # Configurações de debug e logging
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        'DEBUG_MAPEAMENTO_PRODUTOS': os.getenv('DEBUG_MAPEAMENTO_PRODUTOS', 'False').lower() == 'true',
        'DEBUG_ESTRUTURA_PEDIDOS': os.getenv('DEBUG_ESTRUTURA_PEDIDOS', 'False').lower() == 'true',
    }
    
    # Configurações específicas do ambiente
    if usar_ambiente == "producao":
        config.update({
            'SANKHYA_BASE_URL': os.getenv("SANKHYA_BASE_URL"),
            'SANKHYA_APPKEY': os.getenv("SANKHYA_APPKEY"),
            'SANKHYA_TOKEN': os.getenv("SANKHYA_TOKEN"),
        })
        ambiente_msg = "🏭 Ambiente: PRODUÇÃO"
    else:
        config.update({
            'SANKHYA_BASE_URL': os.getenv("SANDBOX_BASE_URL"),
            'SANKHYA_APPKEY': os.getenv("SANDBOX_APPKEY"),
            'SANKHYA_TOKEN': os.getenv("SANDBOX_TOKEN"),
        })
        ambiente_msg = "🧪 Ambiente: SANDBOX"
    
    # CORREÇÃO: Só faz logs na primeira vez
    if not _config_loaded:
        print(f"[CONFIG] {ambiente_msg}")
        
        # Validação de parâmetros obrigatórios
        required_params = [
            'WEBHOOK_SECRET', 'SANKHYA_BASE_URL', 'SANKHYA_APPKEY', 
            'SANKHYA_TOKEN', 'SANKHYA_USERNAME', 'SANKHYA_PASSWORD'
        ]
        
        missing_params = []
        for param in required_params:
            if not config.get(param):
                missing_params.append(param)
        
        if missing_params:
            print(f"[CONFIG] Parâmetros obrigatórios não configurados: {', '.join(missing_params)}")
            raise ValueError(f"Parâmetros obrigatórios não configurados: {', '.join(missing_params)}")
        
        # Validações adicionais para WooCommerce
        wc_params = ['WC_URL', 'WC_KEY', 'WC_SECRET']
        missing_wc = [p for p in wc_params if not config.get(p)]
        
        if missing_wc:
            print(f"[CONFIG] Parâmetros WooCommerce não configurados: {', '.join(missing_wc)}")
            print("[CONFIG] Funcionalidades do WooCommerce podem não funcionar")
        else:
            print("[CONFIG] WooCommerce configurado")
        
        # Validação da URL do WooCommerce
        wc_url = config.get('WC_URL', '')
        if wc_url and not wc_url.endswith('/wp-json/wc/v3'):
            print(f"[CONFIG] WC_URL deveria terminar com '/wp-json/wc/v3': {wc_url}")
        
        # Log das principais configurações (sem dados sensíveis)
        print(f"[CONFIG] Configurações carregadas:")
        print(f"[CONFIG]   Ambiente: {config['USAR_AMBIENTE']}")
        print(f"[CONFIG]   Sankhya URL: {config.get('SANKHYA_BASE_URL', 'N/A')}")
        print(f"[CONFIG]   WooCommerce URL: {config.get('WC_URL', 'N/A')}")
        print(f"[CONFIG]   Produtos - Cache: {config['PRODUTOS_CACHE_TAMANHO']}")
        print(f"[CONFIG]   Produtos - Normalizar SKUs: {config['PRODUTOS_NORMALIZAR_SKUS']}")
        print(f"[CONFIG]   Produtos - Processamento parcial: {config['PRODUTOS_PERMITIR_PROCESSAMENTO_PARCIAL']}")
        print(f"[CONFIG]   Pedidos - Informar preço: {config['PEDIDOS_INFORMAR_PRECO']}")
        print(f"[CONFIG]   Pedidos - TIPMOV: {config['PEDIDOS_TIPMOV_PADRAO']}")
        print(f"[CONFIG]   Transportadoras - Usar padrão: {config['TRANSPORTADORAS_USAR_PADRAO']}")
        print(f"[CONFIG]   Debug - Mapeamento: {config['DEBUG_MAPEAMENTO_PRODUTOS']}")
        print(f"[CONFIG]   Log level: {config['LOG_LEVEL']}")
    
    # Atualiza cache
    _config_cache = config
    _config_loaded = True
    
    if app:
        app.config.update(config)
    
    return config

def get_sankhya_defaults():
    """
    Retorna configurações padrão do Sankhya
    """
    config = load_config()
    
    try:
        defaults = {
            'CODLOCALORIG': int(config['SANKHYA_CODLOCALORIG']),
            'CODTIPOPER': int(config['SANKHYA_CODTIPOPER']),
            'CODTIPVENDA': int(config['SANKHYA_CODTIPVENDA']),
            'CODVEND': int(config['SANKHYA_CODVEND']),
            'CODEMP': int(config['SANKHYA_CODEMP']),
            'CODNAT': int(config['SANKHYA_CODNAT']),
            'TIPMOV': config['PEDIDOS_TIPMOV_PADRAO'] 
        }
        
        return defaults
        
    except ValueError as e:
        if "invalid literal for int()" in str(e):
            raise ValueError("Configurações do Sankhya devem ser números inteiros")
        else:
            raise

def get_produtos_config():
    """
    Retorna configurações específicas para produtos
    """
    config = load_config()
    
    return {
        'cache_tamanho': config['PRODUTOS_CACHE_TAMANHO'],
        'normalizar_skus': config['PRODUTOS_NORMALIZAR_SKUS'],
        'permitir_processamento_parcial': config['PRODUTOS_PERMITIR_PROCESSAMENTO_PARCIAL'],
        'debug_mapeamento': config['DEBUG_MAPEAMENTO_PRODUTOS']
    }

def get_pedidos_config():
    """
    Retorna configurações específicas para pedidos
    """
    config = load_config()
    
    return {
        'informar_preco': config['PEDIDOS_INFORMAR_PRECO'],
        'tipmov_padrao': config['PEDIDOS_TIPMOV_PADRAO'],
        'incluir_observacoes_woo': config['PEDIDOS_INCLUIR_OBSERVACOES_WOO'],
        'debug_estrutura': config['DEBUG_ESTRUTURA_PEDIDOS']
    }

def get_transportadoras_config():
    """
    Retorna configurações específicas para transportadoras
    """
    config = load_config()
    
    return {
        'usar_padrao': config['TRANSPORTADORAS_USAR_PADRAO'],
        'codparc_padrao': config['TRANSPORTADORAS_CODPARC_PADRAO']
    }

def get_webhook_config():
    """
    Retorna configurações específicas para webhooks
    """
    config = load_config()
    
    allowed_ips = []
    if config['WEBHOOK_ALLOWED_IPS']:
        allowed_ips = [ip.strip() for ip in config['WEBHOOK_ALLOWED_IPS'].split(',') if ip.strip()]
    
    return {
        'secret': config['WEBHOOK_SECRET'],
        'wc_secret': config.get('WC_WEBHOOK_SECRET'),
        'allowed_ips': allowed_ips,
        'rate_limit': config['WEBHOOK_RATE_LIMIT'],
        'validar_hmac': config['VALIDAR_HMAC_SIGNATURE']
    }