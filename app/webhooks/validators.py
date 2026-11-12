import uuid
from datetime import datetime, timezone

class WebhookValidator:
    """
    Validador específico para webhooks - VERSÃO CORRIGIDA
    """
    
    @staticmethod
    def validar_headers(headers):
        """
        Valida headers do webhook do WooCommerce
        """
        erros = []
        
        print(f"[WEBHOOK VALIDATOR DEBUG] Headers recebidos: {headers}")
        
        # Headers essenciais do WooCommerce
        if not headers.get('event_type'):
            erros.append("Header 'X-WC-Webhook-Event' não encontrado")
        
        if not headers.get('resource'):
            erros.append("Header 'X-WC-Webhook-Resource' não encontrado")
        
        # Valida valores dos headers se existem
        event_type = headers.get('event_type')
        resource = headers.get('resource')
        
        print(f"[WEBHOOK VALIDATOR DEBUG] Event Type: {event_type}")
        print(f"[WEBHOOK VALIDATOR DEBUG] Resource: {resource}")
        
        if event_type and event_type not in ['created', 'updated', 'deleted', 'restored']:
            erros.append(f"Event type '{event_type}' não é válido")
        
        if resource and resource not in ['order', 'customer', 'product', 'coupon', 'subscription']:
            erros.append(f"Resource '{resource}' não é válido")
        
        # Headers opcionais mas úteis
        webhook_id = headers.get('webhook_id')
        delivery_id = headers.get('delivery_id')
        
        print(f"[WEBHOOK VALIDATOR DEBUG] Webhook ID: {webhook_id}")
        print(f"[WEBHOOK VALIDATOR DEBUG] Delivery ID: {delivery_id}")
        
        if not webhook_id:
            print("[WEBHOOK VALIDATOR DEBUG] Warning: Webhook ID não fornecido")
        
        if not delivery_id:
            print("[WEBHOOK VALIDATOR DEBUG] Warning: Delivery ID não fornecido")
        
        print(f"[WEBHOOK VALIDATOR DEBUG] Validação concluída. Erros: {erros}")
        
        return erros
    
    @staticmethod
    def validar_assinatura(payload, signature, secret):
        """
        Valida assinatura HMAC do webhook
        """
        if not signature or not secret:
            return False
        
        import hmac
        import hashlib
        
        try:
            # WooCommerce envia base64 encoded
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).digest()
            
            import base64
            expected_b64 = base64.b64encode(expected_signature).decode('utf-8')
            
            # Remove prefixo se presente
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            return hmac.compare_digest(expected_b64, signature)
            
        except Exception as e:
            print(f"[WEBHOOK VALIDATOR] Erro na validação de assinatura: {e}")
            return False
    
    @staticmethod
    def validar_payload_estrutura(data):
        """
        Valida estrutura básica do payload
        """
        erros = []
        
        if not isinstance(data, dict):
            erros.append("Payload deve ser um objeto JSON")
            return erros
        
        # ID é essencial em qualquer webhook do WooCommerce
        if not data.get('id'):
            erros.append("ID do objeto não encontrado no payload")
        
        return erros
    
    _rate_store = {}

    @staticmethod
    def validar_rate_limit(identifier, max_requests=100, window_seconds=60):
        """
        Rate limiting por janela deslizante, em memória
        (com vários processos, usar Redis ou banco)
        """
        import time
        from collections import deque
        now = time.time()
        q = WebhookValidator._rate_store.setdefault(identifier, deque())
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= max_requests:
            return False
        q.append(now)
        return True

    @staticmethod
    def normalizar_evento(event_type, resource):
        """
        Normaliza evento para formato padrão
        """
        if not event_type or not resource:
            return None
        
        return f"{resource.lower()}.{event_type.lower()}"
    
    @staticmethod
    def eh_evento_suportado(event_type, resource):
        """
        Verifica se evento é suportado
        """
        eventos_suportados = {
            'order.created',
            'order.updated',
            'order.deleted',
            'order.restored',
            'customer.created',
            'customer.updated',
            'customer.deleted',
            'product.created',
            'product.updated',
            'product.deleted'
        }
        
        evento = WebhookValidator.normalizar_evento(event_type, resource)
        return evento in eventos_suportados
    
    @staticmethod
    def gerar_error_id():
        """
        Gera ID único para tracking de erros
        """
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def agora_iso():
        """
        Retorna timestamp atual em formato ISO
        """
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def extrair_info_debug(headers, data):
        """
        Extrai informações úteis para debug
        """
        info = {
            'webhook_id': headers.get('webhook_id', 'N/A'),
            'delivery_id': headers.get('delivery_id', 'N/A'),
            'event': WebhookValidator.normalizar_evento(
                headers.get('event_type'), 
                headers.get('resource')
            ),
            'source': headers.get('source', 'N/A'),
            'data_id': data.get('id', 'N/A') if isinstance(data, dict) else 'N/A',
            'data_type': type(data).__name__,
            'payload_size': len(str(data)),
            'timestamp': WebhookValidator.agora_iso()
        }
        
        return info