"""
Módulo de serviços para integração com WooCommerce
"""

from .client import WooCommerceClient
from .processors import (
    WooCommerceProcessor,
    processar_pedido_criado,
    processar_cliente_criado,
    processar_pedido_atualizado,
    processar_cliente_atualizado,
    processar_pedido_removido,
    processar_cliente_removido
)
from .validators import WooCommerceValidator
from .mapper import WooCommerceMapper
from .service import WooCommerceService

__all__ = [
    'WooCommerceClient',
    'WooCommerceProcessor',
    'WooCommerceValidator', 
    'WooCommerceMapper',
    'WooCommerceService',
    # Funções de conveniência
    'processar_pedido_criado',
    'processar_cliente_criado',
    'processar_pedido_atualizado',
    'processar_cliente_atualizado',
    'processar_pedido_removido',
    'processar_cliente_removido'
]

# Versão do módulo
__version__ = '2.0.0'