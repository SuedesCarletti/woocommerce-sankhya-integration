"""
Módulo de serviços para integração WooCommerce-Sankhya
"""

# Importações principais para facilitar o uso
from .sankhya import SankhyaService, SankhyaAuth
from .woocommerce import WooCommerceService, WooCommerceClient

__all__ = [
    'SankhyaService',
    'SankhyaAuth', 
    'WooCommerceService',
    'WooCommerceClient'
]

# Versão do módulo de serviços
__version__ = '2.0.0'