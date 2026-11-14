"""
Módulo de serviços para integração com API Sankhya
VERSÃO CORRIGIDA: 2.2.0 - Com context manager corrigido e transportadoras
"""

from .auth import SankhyaAuth
from .base import SankhyaClient
from .cidades import CidadesService
from .parceiros import ParceirosService
from .contatos import ContatosService
from .enderecos import EnderecosService
from .pedidos import PedidosService
from .transportadoras import TransportadorasService
from .produtos import ProdutosService
from .estoque import EstoqueService
from .service import SankhyaService, SankhyaServiceContext

__all__ = [
    # Classes principais
    'SankhyaService',
    'SankhyaServiceContext',  # Context manager corrigido
    
    # Autenticação
    'SankhyaAuth',
    'SankhyaClient',
    
    # Serviços específicos
    'CidadesService',
    'ParceirosService',
    'ContatosService',
    'EnderecosService',
    'PedidosService',
    'TransportadorasService',
    'ProdutosService',
    'EstoqueService'
]

# Versão atualizada com correções
__version__ = '2.2.0'

# Informações da versão
__changelog__ = {
    '2.2.0': [
        'Context manager SankhyaServiceContext corrigido',
        'Correção do erro "str object has no attribute processar_webhook"',
        'Integração order.updated com Sankhya funcional',
        'Busca de clientes apenas por documento existente',
        'Suporte completo a transportadoras',
        'Logs melhorados e tratamento de erros robusto'
    ],
    '2.1.0': [
        'Suporte a transportadoras AllPost',
        'Correção de métodos de parceiros',
        'Melhorias nos logs'
    ],
    '2.0.0': [
        'Arquitetura modular completa',
        'Sistema de segurança robusto',
        'Logging estruturado',
        'Health checks avançados'
    ]
}

def get_version_info():
    """Retorna informações detalhadas da versão"""
    return {
        'version': __version__,
        'changelog': __changelog__.get(__version__, []),
        'services_available': len(__all__),
        'main_service': 'SankhyaService'
    }