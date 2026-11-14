import logging
import sys
from datetime import datetime
from pathlib import Path

class ColoredFormatter(logging.Formatter):
    """
    Formatter com cores para diferentes níveis de log
    """
    
    # Códigos de cor ANSI
    COLORS = {
        'DEBUG': '\033[36m',     # Ciano
        'INFO': '\033[32m',      # Verde
        'WARNING': '\033[33m',   # Amarelo
        'ERROR': '\033[31m',     # Vermelho
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Adiciona cor baseada no nível
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Formata a mensagem original
        formatted = super().format(record)
        
        # Adiciona cor apenas ao nível de log
        if color != self.COLORS['RESET']:
            formatted = formatted.replace(
                record.levelname,
                f"{color}{record.levelname}{reset}"
            )
        
        return formatted

def setup_logger(name, level="INFO", format_string=None):
    """
    Configura logger com formatação personalizada
    """
    if format_string is None:
        format_string = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    
    formatter = logging.Formatter(format_string)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.addHandler(handler)
    
    return logger

def log_request(logger, method, path, ip=None, status=None):
    """
    FUNÇÃO ADICIONAL: Log de requisições HTTP
    """
    if status:
        emoji = "" if status < 400 else "❌"
        message = f"{emoji} {method} {path} - Status: {status}"
    else:
        message = f"📥 {method} {path}"
    
    if ip:
        message += f" - IP: {ip}"
    
    logger.info(message)

def log_webhook(logger, event_type, resource=None, webhook_id=None, data_id=None):
    """
    FUNÇÃO CORRIGIDA: Log formatado para webhooks
    
    Args:
        logger: Logger instance
        event_type: Tipo do evento (created, updated, etc.) OU mensagem completa
        resource: Recurso (order, customer, etc.) - OPCIONAL
        webhook_id: ID do webhook - OPCIONAL  
        data_id: ID dos dados - OPCIONAL
    """
    try:
        # CORREÇÃO: Flexibilidade na assinatura
        if resource is None and webhook_id is None and data_id is None:
            # Modo simples: apenas event_type como mensagem
            message = f"📨 {event_type}"
        else:
            # Modo completo: monta mensagem estruturada
            if resource:
                message = f"📨 Webhook: {resource}.{event_type}"
            else:
                message = f"📨 Webhook: {event_type}"
            
            if webhook_id:
                message += f" | ID: {webhook_id}"
            if data_id:
                message += f" | Data ID: {data_id}"
        
        logger.info(message)
        
    except Exception as e:
        # Fallback seguro
        logger.info(f"Webhook log error: {e} - Event: {event_type}")

def log_processing(logger, process_name, status, details=None):
    """
    Log formatado para processamento
    """
    if status == "start":
        emoji = "🔄"
        level = "info"
        message = f"{emoji} Iniciando: {process_name}"
    elif status == "success":
        emoji = ""
        level = "info"
        message = f"{emoji} Sucesso: {process_name}"
    elif status == "warning":
        emoji = "⚠️"
        level = "warning"
        message = f"{emoji} Aviso: {process_name}"
    elif status == "error":
        emoji = "❌"
        level = "error"
        message = f"{emoji} Erro: {process_name}"
    else:
        emoji = "ℹ️"
        level = "info"
        message = f"{emoji} {process_name}"
    
    if details:
        message += f" | {details}"
    
    getattr(logger, level)(message)

def log_integration_event(logger, event_type, source_id, target_id=None, error=None):
    """
    Log específico para eventos de integração
    """
    if error:
        emoji = "❌"
        level = "error"
        message = f"{emoji} Integração falhou: {event_type} | Source: {source_id}"
        if error:
            message += f" | Erro: {error}"
    else:
        emoji = "🔄"
        level = "info"
        message = f"{emoji} Integração: {event_type} | Source: {source_id}"
        if target_id:
            message += f" | Target: {target_id}"
    
    getattr(logger, level)(message)

def log_data_validation(logger, data_type, validation_result, errors=None):
    """
    Log para validação de dados
    CORRIGIDO: Suporte a diferentes tipos de errors
    """
    if validation_result == "success" or validation_result is True:
        logger.info(f"Sucesso: {data_type}")
    elif validation_result == "error" or validation_result is False:
        message = f"❌ Erro: {data_type}"
        if errors:
            if isinstance(errors, str):
                message += f" | {errors}"
            elif isinstance(errors, list):
                message += f" | Erros: {', '.join(errors)}"
            else:
                message += f" | {str(errors)}"
        logger.error(message)
    else:
        # Para outros tipos de validation_result
        logger.info(f"{data_type}: {validation_result}")

class LogContext:
    """
    Context manager para adicionar contexto aos logs
    """
    
    def __init__(self, logger, context_name):
        self.logger = logger
        self.context_name = context_name
        self.original_formatter = None
    
    def __enter__(self):
        # Adiciona contexto ao formatter
        handler = self.logger.handlers[0] if self.logger.handlers else None
        if handler:
            self.original_formatter = handler.formatter
            new_format = f"%(asctime)s | %(name)s | [{self.context_name}] | %(levelname)s | %(message)s"
            handler.setFormatter(logging.Formatter(new_format))
        
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restaura formatter original
        handler = self.logger.handlers[0] if self.logger.handlers else None
        if handler and self.original_formatter:
            handler.setFormatter(self.original_formatter)

# LOGGER PADRÃO E FUNÇÕES DE CONVENIÊNCIA

# Logger padrão para uso geral
default_logger = setup_logger("app")

def info(message):
    """Função de conveniência para log info"""
    default_logger.info(message)

def warning(message):
    """Função de conveniência para log warning"""
    default_logger.warning(message)

def error(message):
    """Função de conveniência para log error"""
    default_logger.error(message)

def debug(message):
    """Função de conveniência para log debug"""
    default_logger.debug(message)

# COMPATIBILIDADE COM VERSÃO ANTERIOR

def log_webhook_legacy(logger, message, data=None):
    """
    FUNÇÃO DE COMPATIBILIDADE: Para código que usa assinatura antiga
    """
    if data:
        log_webhook(logger, message, data_id=str(data))
    else:
        log_webhook(logger, message)
