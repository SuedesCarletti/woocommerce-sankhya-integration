"""
Módulo de webhooks para integração WooCommerce-Sankhya
"""

from .handlers import webhook_bp
from .validators import WebhookValidator
from .security import WebhookSecurity
from .middleware import (
    webhook_middleware,
    log_webhook_metrics,
    validate_webhook_headers,
    require_webhook_token,
    verify_webhook_signature,
    WebhookContext
)

__all__ = [
    'webhook_bp',
    'WebhookValidator',
    'WebhookSecurity',
    'webhook_middleware',
    'log_webhook_metrics',
    'validate_webhook_headers',
    'require_webhook_token',
    'verify_webhook_signature',
    'WebhookContext'
]

# Versão do módulo
__version__ = '2.0.0'