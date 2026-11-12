import re
from datetime import datetime

def validar_email(email):
    """
    Validação robusta de email
    """
    if not email or not isinstance(email, str):
        return False
    
    # Pattern básico mas eficiente
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None

def validar_telefone(telefone):
    """
    Validação e formatação de telefone brasileiro
    Remove formatação e valida estrutura
    """
    if not telefone:
        return ""
    
    # Remove tudo que não é número
    numero_limpo = re.sub(r'\D', '', str(telefone))
    
    # Valida tamanho (10-11 dígitos para fixo/celular)
    if len(numero_limpo) < 10 or len(numero_limpo) > 11:
        return ""
    
    # Se tem 10 dígitos, deve começar com código de área válido
    if len(numero_limpo) == 10:
        ddd = numero_limpo[:2]
        if not _validar_ddd(ddd):
            return ""
    
    # Se tem 11 dígitos, deve ser celular (9 no início do número)
    if len(numero_limpo) == 11:
        ddd = numero_limpo[:2]
        primeiro_digito = numero_limpo[2]
        if not _validar_ddd(ddd) or primeiro_digito != '9':
            return ""
    
    return numero_limpo

def _validar_ddd(ddd):
    """
    Valida códigos de área (DDD) brasileiros
    """
    ddds_validos = {
        '11', '12', '13', '14', '15', '16', '17', '18', '19',  # SP
        '21', '22', '24',  # RJ/ES
        '27', '28',  # ES
        '31', '32', '33', '34', '35', '37', '38',  # MG
        '41', '42', '43', '44', '45', '46',  # PR
        '47', '48', '49',  # SC
        '51', '53', '54', '55',  # RS
        '61',  # DF/GO
        '62', '64',  # GO/TO
        '63',  # TO
        '65', '66',  # MT
        '67',  # MS
        '68',  # AC
        '69',  # RO
        '71', '73', '74', '75', '77',  # BA
        '79',  # SE
        '81', '87',  # PE
        '82',  # AL
        '83',  # PB
        '84',  # RN
        '85', '88',  # CE
        '86', '89',  # PI
        '91', '93', '94',  # PA
        '92', '97',  # AM
        '95',  # RR
        '96',  # AP
        '98', '99'   # MA
    }
    return ddd in ddds_validos

def limpar_documento(documento):
    """
    Remove formatação de CPF/CNPJ
    """
    if not documento:
        return ""
    return re.sub(r'\D', '', str(documento))

def validar_cpf(cpf):
    """
    Valida CPF brasileiro
    """
    cpf_limpo = limpar_documento(cpf)
    
    if len(cpf_limpo) != 11:
        return False
    
    # Verifica se não são todos iguais
    if cpf_limpo == cpf_limpo[0] * 11:
        return False
    
    # Validação do primeiro dígito
    soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    primeiro_digito = 0 if resto < 2 else 11 - resto
    
    if int(cpf_limpo[9]) != primeiro_digito:
        return False
    
    # Validação do segundo dígito
    soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    segundo_digito = 0 if resto < 2 else 11 - resto
    
    return int(cpf_limpo[10]) == segundo_digito

def validar_cnpj(cnpj):
    """
    Valida CNPJ brasileiro
    """
    cnpj_limpo = limpar_documento(cnpj)
    
    if len(cnpj_limpo) != 14:
        return False
    
    # Verifica se não são todos iguais
    if cnpj_limpo == cnpj_limpo[0] * 14:
        return False
    
    # Validação do primeiro dígito
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj_limpo[i]) * multiplicadores1[i] for i in range(12))
    resto = soma % 11
    primeiro_digito = 0 if resto < 2 else 11 - resto
    
    if int(cnpj_limpo[12]) != primeiro_digito:
        return False
    
    # Validação do segundo dígito
    multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj_limpo[i]) * multiplicadores2[i] for i in range(13))
    resto = soma % 11
    segundo_digito = 0 if resto < 2 else 11 - resto
    
    return int(cnpj_limpo[13]) == segundo_digito

def validar_documento(documento):
    """
    Valida CPF ou CNPJ automaticamente
    """
    documento_limpo = limpar_documento(documento)
    
    if len(documento_limpo) == 11:
        return validar_cpf(documento_limpo)
    elif len(documento_limpo) == 14:
        return validar_cnpj(documento_limpo)
    else:
        return False

def validar_cep(cep):
    """
    Valida CEP brasileiro
    """
    if not cep:
        return False
    
    cep_limpo = re.sub(r'\D', '', str(cep))
    return len(cep_limpo) == 8

def formatar_cep(cep):
    """
    Formata CEP no padrão XXXXX-XXX
    """
    cep_limpo = re.sub(r'\D', '', str(cep))
    if len(cep_limpo) == 8:
        return f"{cep_limpo[:5]}-{cep_limpo[5:]}"
    return cep_limpo

def validar_data(data_str, formato="%d/%m/%Y"):
    """
    Valida string de data
    """
    if not data_str:
        return False
    
    try:
        datetime.strptime(data_str, formato)
        return True
    except ValueError:
        return False

def validar_url(url):
    """
    Validação básica de URL
    """
    if not url:
        return False
    
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?$'
    return re.match(pattern, url) is not None

def validar_numero_positivo(valor):
    """
    Valida se é um número positivo
    """
    try:
        numero = float(valor)
        return numero > 0
    except (ValueError, TypeError):
        return False

def validar_inteiro_positivo(valor):
    """
    Valida se é um inteiro positivo
    """
    try:
        numero = int(valor)
        return numero > 0
    except (ValueError, TypeError):
        return False

def validar_campo_obrigatorio(valor, nome_campo="Campo"):
    """
    Valida se campo obrigatório não está vazio
    """
    if not valor or (isinstance(valor, str) and not valor.strip()):
        return False, f"{nome_campo} é obrigatório"
    return True, ""

def validar_tamanho_string(valor, min_len=None, max_len=None, nome_campo="Campo"):
    """
    Valida tamanho de string
    """
    if not isinstance(valor, str):
        return False, f"{nome_campo} deve ser texto"
    
    tamanho = len(valor.strip())
    
    if min_len and tamanho < min_len:
        return False, f"{nome_campo} deve ter pelo menos {min_len} caracteres"
    
    if max_len and tamanho > max_len:
        return False, f"{nome_campo} deve ter no máximo {max_len} caracteres"
    
    return True, ""
