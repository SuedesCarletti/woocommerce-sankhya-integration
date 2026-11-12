"""
Módulo de utilitários para a integração WooCommerce-Sankhya
"""

# Importações principais do normalize (manter compatibilidade)
from .normalize import (
    normalizar_nome,
    extrair_keywords, 
    fuzzy_match,
    STOPWORDS
)

# Validadores
from .validators import (
    validar_email,
    validar_telefone,
    limpar_documento,
    validar_cpf,
    validar_cnpj,
    validar_documento,
    validar_cep,
    validar_data,
    validar_url,
    validar_numero_positivo,
    validar_inteiro_positivo,
    validar_campo_obrigatorio,
    validar_tamanho_string
)

# MUDANÇA: Importa de .common ao invés de .formatters
from .common import (
    # Funções de formatters.py (consolidadas)
    formatar_cpf,
    formatar_cnpj,
    formatar_documento,
    formatar_telefone,
    formatar_cep,
    formatar_moeda,
    formatar_percentual,
    formatar_data_brasileira,
    formatar_data_hora_brasileira,
    formatar_nome_proprio,
    formatar_endereco,
    truncar_texto,
    formatar_lista_para_texto,
    sanitizar_filename,
    
    # Funções de helpers.py (consolidadas)
    eh_json_valido,
    pretty_json,
    compactar_json,
    extrair_numeros,
    primeiro_numero,
    limpar_html,
    contar_palavras,
    bytes_para_humano,
    segundos_para_humano,
    obter_extensao_arquivo,
    eh_url_valida,
    normalizar_url,
    extrair_dominio,
    merge_dicts,
    mascarar_dados_sensiveis,
    
    # Aliases para compatibilidade
    formatar_cpf_cnpj,
    normalize_text,
    format_phone,
    format_cpf_cnpj,
    validate_email as validate_email_alias
)

# Utilitários de data
from .dates import (
    agora,
    agora_utc,
    hoje,
    ontem,
    amanha,
    inicio_do_mes,
    fim_do_mes,
    inicio_do_ano,
    fim_do_ano,
    parsear_data_brasileira,
    parsear_data_sankhya,
    data_para_sankhya,
    parsear_data_woocommerce,
    idade_em_anos,
    diferenca_em_dias,
    eh_dia_util,
    proximo_dia_util,
    eh_fim_de_semana,
    nome_do_mes,
    nome_do_dia_semana,
    tempo_relativo,
    timestamp_para_data,
    data_para_timestamp
)

# Logger
from .logger import (
    setup_logger,
    log_request,
    log_webhook,
    log_processing,
    log_integration_event,
    log_data_validation,
    LogContext,
    default_logger,
    info,
    warning,
    error,
    debug
)

__all__ = [
    # Normalize (compatibilidade)
    'normalizar_nome',
    'extrair_keywords',
    'fuzzy_match',
    'STOPWORDS',
    
    # Validators
    'validar_email',
    'validar_telefone', 
    'limpar_documento',
    'validar_cpf',
    'validar_cnpj',
    'validar_documento',
    'validar_cep',
    'validar_data',
    'validar_url',
    'validar_numero_positivo',
    'validar_inteiro_positivo',
    'validar_campo_obrigatorio',
    'validar_tamanho_string',
    
    # Formatters (agora de common.py)
    'formatar_cpf',
    'formatar_cnpj',
    'formatar_documento',
    'formatar_telefone',
    'formatar_cep',
    'formatar_moeda',
    'formatar_percentual',
    'formatar_data_brasileira',
    'formatar_data_hora_brasileira',
    'formatar_nome_proprio',
    'formatar_endereco',
    'truncar_texto',
    'formatar_lista_para_texto',
    'sanitizar_filename',
    
    # Helpers (agora de common.py)
    'eh_json_valido',
    'pretty_json',
    'compactar_json',
    'extrair_numeros',
    'primeiro_numero',
    'limpar_html',
    'contar_palavras',
    'bytes_para_humano',
    'segundos_para_humano',
    'obter_extensao_arquivo',
    'eh_url_valida',
    'normalizar_url',
    'extrair_dominio',
    'merge_dicts',
    'mascarar_dados_sensiveis',
    
    # Aliases
    'formatar_cpf_cnpj',
    'normalize_text',
    'format_phone',
    'format_cpf_cnpj',
    'validate_email_alias',
    
    # Dates
    'agora',
    'agora_utc',
    'hoje',
    'ontem',
    'amanha',
    'inicio_do_mes',
    'fim_do_mes',
    'inicio_do_ano',
    'fim_do_ano',
    'parsear_data_brasileira',
    'parsear_data_sankhya',
    'data_para_sankhya',
    'parsear_data_woocommerce',
    'idade_em_anos',
    'diferenca_em_dias',
    'eh_dia_util',
    'proximo_dia_util',
    'eh_fim_de_semana',
    'nome_do_mes',
    'nome_do_dia_semana',
    'tempo_relativo',
    'timestamp_para_data',
    'data_para_timestamp',
    
    # Logger
    'setup_logger',
    'log_request',
    'log_webhook',
    'log_processing',
    'log_integration_event',
    'log_data_validation',
    'LogContext',
    'default_logger',
    'info',
    'warning',
    'error',
    'debug'
]

# Versão do módulo
__version__ = '2.0.0'
