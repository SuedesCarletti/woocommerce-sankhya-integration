from flask import request, jsonify, g
from functools import wraps
from .security import WebhookSecurity
from .validators import WebhookValidator
from utils import setup_logger
import time

logger = setup_logger("webhook_middleware")
security = WebhookSecurity()
validator = WebhookValidator()

def webhook_middleware(f):
    """
    Middleware para aplicar validações de segurança em webhooks
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Registra início da requisição
        g.start_time = time.time()
        g.request_id = validator.gerar_error_id()
        
        # Log da requisição
        logger.info(f"[{g.request_id}] Webhook received: {request.method} {request.path}")
        
        # Validações de segurança
        security_checks = run_security_checks()
        if security_checks['blocked']:
            logger.warning(f"[{g.request_id}] Request blocked: {security_checks['reason']}")
            return jsonify({
                "status": "error",
                "message": security_checks['reason'],
                "request_id": g.request_id
            }), security_checks['status_code']
        
        # Adiciona informações ao contexto
        g.security_info = security_checks['info']
        
        try:
            # Executa função original
            response = f(*args, **kwargs)
            
            # Log de sucesso
            duration = time.time() - g.start_time
            logger.info(f"[{g.request_id}] Request completed in {duration:.3f}s")
            
            return response
            
        except Exception as e:
            # Log de erro
            duration = time.time() - g.start_time
            logger.error(f"[{g.request_id}] Request failed after {duration:.3f}s: {str(e)}")
            raise
    
    return decorated_function

def run_security_checks():
    """
    Executa todas as verificações de segurança
    """
    # 1. Rate limiting
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    if not security.verificar_rate_limit(client_ip):
        return {
            'blocked': True,
            'reason': 'Rate limit exceeded',
            'status_code': 429,
            'info': {}
        }
    
    # 2. Validação de IP (se configurada)
    if not security.validar_ip_origem(client_ip):
        security.log_security_event("UNAUTHORIZED_IP", f"IP: {client_ip}", "warning")
        return {
            'blocked': True,
            'reason': 'IP not authorized',
            'status_code': 403,
            'info': {}
        }
    
    # 3. Validação de User-Agent (se configurada) 
    user_agent = request.headers.get('User-Agent', '')
    if not security.validar_user_agent(user_agent):
        security.log_security_event("SUSPICIOUS_USER_AGENT", f"Agent: {user_agent}", "warning")
        # Não bloqueia, apenas registra
    
    # 4. Verificação de tamanho do payload
    content_length = request.content_length or 0
    if content_length > 5 * 1024 * 1024:  # 5MB
        return {
            'blocked': True,
            'reason': 'Payload too large',
            'status_code': 413,
            'info': {}
        }
    
    return {
        'blocked': False,
        'reason': None,
        'status_code': 200,
        'info': {
            'client_ip': client_ip,
            'user_agent': user_agent,
            'content_length': content_length,
            'rate_limit_stats': security.obter_estatisticas_rate_limit(client_ip)
        }
    }

def log_webhook_metrics():
    """
    Decorator para logging de métricas de webhook
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log métricas de sucesso
                logger.info(f"Webhook processed successfully in {duration:.3f}s")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log métricas de erro
                logger.error(f"Webhook failed after {duration:.3f}s: {str(e)}")
                raise
        
        return decorated_function
    return decorator

def validate_webhook_headers():
    """
    Decorator para validação de headers de webhook
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            headers = {
                'event_type': request.headers.get("X-WC-Webhook-Event"),
                'resource': request.headers.get("X-WC-Webhook-Resource"),
                'webhook_id': request.headers.get("X-WC-Webhook-ID"),
                'delivery_id': request.headers.get("X-WC-Webhook-Delivery-ID"),
                'signature': request.headers.get("X-WC-Webhook-Signature")
            }
            
            # Validação básica
            erros = validator.validar_headers(headers)
            if erros:
                return jsonify({
                    "status": "error",
                    "message": "Invalid headers",
                    "errors": erros
                }), 400
            
            # Adiciona headers ao contexto
            g.webhook_headers = headers
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_webhook_token():
    """
    Decorator para exigir token válido
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.args.get("token")
            
            if not security.validar_token(token):
                return jsonify({"erro": "Token inválido"}), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def verify_webhook_signature():
    """
    Decorator para verificação de assinatura HMAC
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            signature = request.headers.get("X-WC-Webhook-Signature")
            
            if signature:
                if not security.validar_assinatura(request.data, signature):
                    security.log_security_event("INVALID_SIGNATURE", f"IP: {request.remote_addr}", "error")
                    return jsonify({"erro": "Assinatura inválida"}), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

class WebhookContext:
    """
    Context manager para webhooks com cleanup automático
    """
    
    def __init__(self, webhook_id=None):
        self.webhook_id = webhook_id or validator.gerar_error_id()
        self.start_time = None
        self.logger = setup_logger(f"webhook_{self.webhook_id}")
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting webhook processing: {self.webhook_id}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Webhook {self.webhook_id} completed successfully in {duration:.3f}s")
        else:
            self.logger.error(f"Webhook {self.webhook_id} failed after {duration:.3f}s: {exc_val}")
        
        # Cleanup de rate limit cache periodicamente
        if hasattr(security, 'limpar_cache_rate_limit'):
            security.limpar_cache_rate_limit()
    
    def log_event(self, message, level="info"):
        """
        Log evento dentro do contexto do webhook
        """
        getattr(self.logger, level)(f"[{self.webhook_id}] {message}")
    
    def log_processing_step(self, step, status, details=None):
        """
        Log passo específico do processamento
        """
        message = f"Step '{step}': {status}"
        if details:
            message += f" - {details}"
        
        self.log_event(message, "info" if status == "success" else "warning")