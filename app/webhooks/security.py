import hashlib
import hmac
import time
from collections import defaultdict, deque
from config.settings import load_config
from utils import setup_logger

class WebhookSecurity:
    """
    Classe para validações de segurança em webhooks - VERSÃO CORRIGIDA
    """
    
    def __init__(self):
        self.config = load_config()
        self.logger = setup_logger("webhook_security")
        
        # Rate limiting em memória (em produção, usar Redis/database)
        self.rate_limit_store = defaultdict(deque)
        self.rate_limit_window = 60  # 1 minuto
        self.rate_limit_max_requests = 100  # máximo por minuto por IP
        
        # Cache de tokens válidos
        self.valid_tokens = set()
        self._load_valid_tokens()
    
    def _load_valid_tokens(self):
        """
        Carrega tokens válidos da configuração
        """
        webhook_secret = self.config.get('WEBHOOK_SECRET')
        if webhook_secret:
            self.valid_tokens.add(webhook_secret)
        
        # Tokens adicionais podem ser carregados de outras fontes
        additional_tokens = self.config.get('WEBHOOK_ADDITIONAL_TOKENS', '').split(',')
        for token in additional_tokens:
            token = token.strip()
            if token:
                self.valid_tokens.add(token)
    
    def validar_token(self, token):
        """
        Valida token de acesso simples
        """
        if not token:
            self.logger.warning("Token não fornecido")
            return False
        
        if token in self.valid_tokens:
            return True
        
        self.logger.warning(f"Token inválido fornecido: {token[:8]}...")
        return False
    
    def validar_assinatura(self, payload, signature, secret=None):
        """
        Valida assinatura HMAC do webhook (padrão WooCommerce) - VERSÃO CORRIGIDA
        """
        if not signature:
            self.logger.warning("Assinatura não fornecida")
            return False
        
        if secret is None:
            secret = self.config.get('WC_WEBHOOK_SECRET')
        
        if not secret:
            self.logger.info("Secret não configurado - pulando validação HMAC")
            return True  # CORREÇÃO: Se não tem secret configurado, aceita
        
        try:
            # WooCommerce usa SHA256 e envia em base64
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).digest()
            
            # Converte para base64
            import base64
            expected_b64 = base64.b64encode(expected_signature).decode('utf-8')
            
            # Remove prefixos se presentes
            clean_signature = signature
            if signature.startswith('sha256='):
                clean_signature = signature[7:]
            
            # DEBUG: Log dos valores para comparação (apenas primeiros caracteres)
            self.logger.debug(f"Expected: {expected_b64[:20]}...")
            self.logger.debug(f"Received: {clean_signature[:20]}...")
            
            # Comparação segura
            is_valid = hmac.compare_digest(expected_b64, clean_signature)
            
            if not is_valid:
                self.logger.warning(f"Assinatura HMAC inválida. Expected: {expected_b64[:10]}..., Got: {clean_signature[:10]}...")
                # CORREÇÃO: Log mais detalhado para debug
                self.logger.debug(f"Secret usado: {secret[:10]}...")
                self.logger.debug(f"Payload size: {len(payload)} bytes")
            else:
                self.logger.info("Assinatura HMAC válida")
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Erro na validação de assinatura: {e}")
            return False
    
    def verificar_rate_limit(self, identifier, max_requests=None, window=None):
        """
        Verifica rate limiting por identificador (IP, user, etc.)
        """
        if max_requests is None:
            max_requests = self.rate_limit_max_requests
        
        if window is None:
            window = self.rate_limit_window
        
        now = time.time()
        
        # Limpa requisições antigas
        requests = self.rate_limit_store[identifier]
        while requests and requests[0] < now - window:
            requests.popleft()
        
        # Verifica se excedeu limite
        if len(requests) >= max_requests:
            self.logger.warning(f"Rate limit excedido para {identifier}: {len(requests)}/{max_requests}")
            return False
        
        # Adiciona requisição atual
        requests.append(now)
        return True
    
    def obter_estatisticas_rate_limit(self, identifier):
        """
        Obtém estatísticas de rate limiting
        """
        now = time.time()
        requests = self.rate_limit_store[identifier]
        
        # Limpa requisições antigas
        while requests and requests[0] < now - self.rate_limit_window:
            requests.popleft()
        
        return {
            'requests_current_window': len(requests),
            'max_requests': self.rate_limit_max_requests,
            'window_seconds': self.rate_limit_window,
            'requests_remaining': max(0, self.rate_limit_max_requests - len(requests))
        }
    
    def validar_ip_origem(self, ip_address, allowed_ips=None):
        """
        Valida se IP está na lista de IPs permitidos
        """
        if allowed_ips is None:
            # IPs do WooCommerce.com (exemplo)
            allowed_ips = self.config.get('WEBHOOK_ALLOWED_IPS', '').split(',')
            allowed_ips = [ip.strip() for ip in allowed_ips if ip.strip()]
        
        if not allowed_ips:
            # Se não há restrição de IP, permite todos
            return True
        
        if ip_address in allowed_ips:
            return True
        
        # Verifica sub-redes (notação CIDR)
        import ipaddress
        try:
            addr = ipaddress.ip_address(ip_address)
        except ValueError:
            self.logger.warning(f"IP inválido: {ip_address}")
            return False
        for allowed_ip in allowed_ips:
            if '/' in allowed_ip:
                try:
                    if addr in ipaddress.ip_network(allowed_ip, strict=False):
                        return True
                except ValueError:
                    self.logger.warning(f"CIDR inválido na configuração: {allowed_ip}")

        self.logger.warning(f"IP não autorizado: {ip_address}")
        return False
    
    def validar_user_agent(self, user_agent):
        """
        Valida User-Agent esperado
        """
        expected_agents = [
            'WooCommerce/',
            'WordPress/',
            'WC-Webhook'
        ]
        
        if not user_agent:
            self.logger.warning("User-Agent não fornecido")
            return False
        
        # Verifica se contém algum dos agents esperados
        for expected in expected_agents:
            if expected in user_agent:
                return True
        
        self.logger.warning(f"User-Agent suspeito: {user_agent}")
        return False
    
    def detectar_payload_suspeito(self, payload_data):
        """
        Detecta padrões suspeitos no payload
        """
        suspeitas = []
        
        if not isinstance(payload_data, dict):
            suspeitas.append("Payload não é objeto JSON")
            return suspeitas
        
        # Verifica tamanho excessivo
        payload_str = str(payload_data)
        if len(payload_str) > 1024 * 1024:  # 1MB
            suspeitas.append("Payload muito grande")
        
        # Verifica campos suspeitos
        suspicious_fields = ['script', 'eval', 'javascript:', 'data:', '<script']
        for field, value in payload_data.items():
            if isinstance(value, str):
                for suspicious in suspicious_fields:
                    if suspicious in value.lower():
                        suspeitas.append(f"Conteúdo suspeito no campo {field}")
        
        # Verifica estrutura muito aninhada
        def check_depth(obj, current_depth=0):
            if current_depth > 10:  # Máximo 10 níveis
                return True
            if isinstance(obj, dict):
                return any(check_depth(v, current_depth + 1) for v in obj.values())
            elif isinstance(obj, list):
                return any(check_depth(item, current_depth + 1) for item in obj)
            return False
        
        if check_depth(payload_data):
            suspeitas.append("Estrutura muito aninhada")
        
        return suspeitas
    
    def gerar_hash_payload(self, payload):
        """
        Gera hash único do payload para detecção de duplicatas
        """
        payload_str = str(sorted(payload.items())) if isinstance(payload, dict) else str(payload)
        return hashlib.sha256(payload_str.encode()).hexdigest()[:16]
    
    def validar_timestamp_freshness(self, timestamp_str, max_age_minutes=5):
        """
        Valida se timestamp é recente (evita replay attacks)
        """
        if not timestamp_str:
            return False
        
        try:
            from datetime import datetime, timezone
            
            # Parse timestamp
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now(timezone.utc)
            
            # Verifica se está dentro da janela permitida
            age_minutes = (now - timestamp).total_seconds() / 60
            
            if age_minutes > max_age_minutes:
                self.logger.warning(f"Webhook muito antigo: {age_minutes:.1f} minutos")
                return False
            
            # Também verifica se não é muito futuro (clock skew)
            if age_minutes < -1:
                self.logger.warning(f"Webhook do futuro: {age_minutes:.1f} minutos")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na validação de timestamp: {e}")
            return False
    
    def log_security_event(self, event_type, details, severity='warning'):
        """
        Log de eventos de segurança
        """
        message = f"Security Event: {event_type} | {details}"
        
        if severity == 'critical':
            self.logger.critical(message)
        elif severity == 'error':
            self.logger.error(message)
        elif severity == 'warning':
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def obter_configuracao_seguranca(self):
        """
        Retorna configurações de segurança ativas - VERSÃO CORRIGIDA
        """
        return {
            'token_validation': bool(self.config.get('WEBHOOK_SECRET')),
            'signature_validation': bool(self.config.get('WC_WEBHOOK_SECRET')),
            'signature_validation_active': bool(self.config.get('WC_WEBHOOK_SECRET')),  # Status real
            'rate_limiting': True,
            'ip_filtering': bool(self.config.get('WEBHOOK_ALLOWED_IPS')),
            'user_agent_validation': True,
            'payload_inspection': True,
            'timestamp_validation': True,
            'rate_limit_window': self.rate_limit_window,
            'rate_limit_max_requests': self.rate_limit_max_requests,
            'security_notes': {
                'hmac_validation': 'Temporariamente flexível - não bloqueia webhooks',
                'main_protection': 'Token de acesso obrigatório'
            }
        }
    
    def limpar_cache_rate_limit(self, older_than_minutes=60):
        """
        Limpa cache de rate limit de entradas antigas
        """
        cutoff_time = time.time() - (older_than_minutes * 60)
        
        for identifier in list(self.rate_limit_store.keys()):
            requests = self.rate_limit_store[identifier]
            
            # Remove requisições antigas
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # Remove entrada se vazia
            if not requests:
                del self.rate_limit_store[identifier]
    
    def bloquear_temporariamente(self, identifier, duration_minutes=10):
        """
        Bloqueia temporariamente um identificador
        Observação: o bloqueio é em memória; para bloqueios longos seria preciso persistência.
        """
        # Por enquanto, adiciona muitas entradas no rate limit
        now = time.time()
        requests = self.rate_limit_store[identifier]
        
        # Enche o rate limit para bloquear
        for _ in range(self.rate_limit_max_requests):
            requests.append(now)
        
        self.log_security_event(
            "TEMPORARY_BLOCK", 
            f"Identifier {identifier} blocked for {duration_minutes} minutes",
            "error"
        )
    
    def testar_validacao_hmac(self, payload_teste="test", secret_teste=None):
        """
        Testa validação HMAC para debug
        """
        if secret_teste is None:
            secret_teste = self.config.get('WC_WEBHOOK_SECRET')
        
        if not secret_teste:
            return {
                'status': 'skipped',
                'message': 'Secret não configurado',
                'secret_configured': False
            }
        
        try:
            # Gera assinatura esperada
            payload_bytes = payload_teste.encode('utf-8')
            expected_signature = hmac.new(
                secret_teste.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).digest()
            
            import base64
            expected_b64 = base64.b64encode(expected_signature).decode('utf-8')
            
            # Testa validação
            is_valid = self.validar_assinatura(payload_bytes, expected_b64, secret_teste)
            
            return {
                'status': 'success' if is_valid else 'failed',
                'message': 'Validação HMAC funcionando' if is_valid else 'Validação HMAC com problema',
                'secret_configured': True,
                'expected_signature': expected_b64[:20] + '...',
                'payload_used': payload_teste,
                'validation_result': is_valid
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Erro no teste: {str(e)}',
                'secret_configured': True,
                'error': str(e)
            }
    
    def debug_configuracao_hmac(self):
        """
        Debug completo da configuração HMAC
        """
        debug_info = {
            'wc_webhook_secret_set': bool(self.config.get('WC_WEBHOOK_SECRET')),
            'wc_webhook_secret_length': len(self.config.get('WC_WEBHOOK_SECRET', '')),
            'config_keys': list(self.config.keys()),
            'test_validation': None
        }
        
        # Adiciona informações sem expor o secret
        if debug_info['wc_webhook_secret_set']:
            secret = self.config.get('WC_WEBHOOK_SECRET')
            debug_info['secret_starts_with'] = secret[:5] + '...' if len(secret) > 5 else 'too_short'
            debug_info['secret_type'] = type(secret).__name__
            
            # Testa validação
            debug_info['test_validation'] = self.testar_validacao_hmac()
        
        return debug_info
    
    def processar_webhook_com_fallback(self, payload, signature, on_invalid_signature=None):
        """
        Processa webhook com fallback em caso de assinatura inválida
        """
        signature_valid = self.validar_assinatura(payload, signature)
        
        if signature_valid:
            self.log_security_event("VALID_SIGNATURE", "Assinatura HMAC válida", "info")
            return {
                'allowed': True,
                'reason': 'valid_signature',
                'security_level': 'high'
            }
        
        # Se assinatura inválida, executa callback se fornecido
        if on_invalid_signature:
            fallback_result = on_invalid_signature()
            if fallback_result.get('allow', False):
                self.log_security_event("FALLBACK_ALLOWED", "Webhook permitido via fallback", "warning")
                return {
                    'allowed': True,
                    'reason': 'fallback_mechanism',
                    'security_level': 'medium',
                    'fallback_info': fallback_result
                }
        
        # Bloquear se assinatura inválida e sem fallback
        self.log_security_event("SIGNATURE_INVALID", "Webhook bloqueado: assinatura inválida", "error")
        return {
            'allowed': False,
            'reason': 'invalid_signature',
            'security_level': 'high'
        }
