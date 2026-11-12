import re
from rapidfuzz import process, fuzz

# Lista padrão de stopwords para endereços e bairros
STOPWORDS = {
    "RUA", "AV", "AVENIDA", "TRAVESSA", "TRAV", "ALAMEDA", "ESTRADA",
    "RODOVIA", "PRACA", "PRAÇA", "VILA", "JD", "JARDIM", "RESIDENCIAL",
    "CONJUNTO", "SITIO", "SÍTIO", "LARGO", "LADEIRA", "DISTRITO", "PQ", "PARQUE"
}

def normalizar_nome(nome):
    """
    Padroniza um nome para caixa alta, remove espaços duplicados e acentuação.
    """
    if not nome:
        return ""
        
    nome = str(nome).upper()
    nome = re.sub(r'\s+', ' ', nome)
    nome = nome.replace('Á','A').replace('Ã','A').replace('Â','A').replace('À','A')
    nome = nome.replace('É','E').replace('Ê','E')
    nome = nome.replace('Í','I')
    nome = nome.replace('Ó','O').replace('Õ','O').replace('Ô','O')
    nome = nome.replace('Ú','U')
    nome = nome.replace('Ç','C')
    return nome.strip()

def extrair_keywords(nome):
    """
    Remove stopwords de nomes e retorna apenas as palavras relevantes.
    """
    nome = normalizar_nome(nome)
    palavras = nome.split()
    return [p for p in palavras if p not in STOPWORDS]

def fuzzy_match(target, lista, threshold=85):
    """
    Faz fuzzy matching entre o alvo e uma lista, retornando o melhor match se acima do threshold.
    """
    if not lista or not target:
        return None
    result = process.extractOne(target, lista, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        return result[0]
    return None

def limpar_documento(documento):
    """
    Remove formatação de CPF/CNPJ
    """
    if not documento:
        return ""
    return documento.replace('.', '').replace('-', '').replace('/', '').strip()

def validar_email(email):
    """
    Validação básica de email
    """
    if not email:
        return False
    return '@' in email and '.' in email.split('@')[-1]

def validar_telefone(telefone):
    """
    Validação básica de telefone (remove formatação)
    """
    if not telefone:
        return ""
    # Remove tudo que não é número
    numero_limpo = re.sub(r'\D', '', telefone)
    return numero_limpo if len(numero_limpo) >= 10 else ""