"""
Utils Consolidados - WooCommerce-Sankhya Integration
Consolida TODAS as funções de utils/helpers.py + utils/formatters.py
Mantém compatibilidade total com código existente
"""

import re
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

# FUNÇÕES DE utils/helpers.py (REAIS)

def eh_json_valido(texto):
    """
    Verifica se string é JSON válido
    """
    try:
        json.loads(texto)
        return True
    except (ValueError, TypeError):
        return False

def pretty_json(obj, indent=2):
    """
    Formata objeto como JSON identado
    """
    return json.dumps(obj, indent=indent, ensure_ascii=False, default=str)

def compactar_json(obj):
    """
    Compacta objeto para JSON sem espaços
    """
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=False, default=str)

def extrair_numeros(texto):
    """
    Extrai todos os números de um texto
    """
    return re.findall(r'\d+\.?\d*', texto)

def primeiro_numero(texto):
    """
    Extrai primeiro número de um texto
    """
    numeros = extrair_numeros(texto)
    return float(numeros[0]) if numeros else None

def limpar_html(texto):
    """
    Remove tags HTML de um texto
    """
    import re
    return re.sub(r'<[^>]+>', '', texto)

def contar_palavras(texto):
    """
    Conta palavras em um texto
    """
    if not texto:
        return 0
    return len(texto.split())

def bytes_para_humano(bytes_value):
    """
    Converte bytes para formato legível
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"

def segundos_para_humano(segundos):
    """
    Converte segundos para formato legível
    """
    if segundos < 60:
        return f"{segundos:.1f}s"
    elif segundos < 3600:
        return f"{segundos/60:.1f}m"
    elif segundos < 86400:
        return f"{segundos/3600:.1f}h"
    else:
        return f"{segundos/86400:.1f}d"

def obter_extensao_arquivo(filename):
    """
    Obtém extensão de arquivo
    """
    return filename.split('.')[-1].lower() if '.' in filename else ''

def eh_url_valida(url):
    """
    Verificação básica se string é URL válida
    """
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?$'
    return re.match(pattern, url) is not None

def normalizar_url(url):
    """
    Normaliza URL removendo barra final e convertendo para minúsculo
    """
    if not url:
        return ""
    
    url = url.strip().lower()
    if url.endswith('/'):
        url = url[:-1]
    return url

def extrair_dominio(url):
    """
    Extrai domínio de uma URL
    """
    pattern = r'https?://(?:www\.)?([^/]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else url

def merge_dicts(*dicts, deep=False):
    """
    Mescla múltiplos dicionários
    """
    if not deep:
        result = {}
        for d in dicts:
            result.update(d)
        return result
    
    # Merge profundo
    def deep_merge(dict1, dict2):
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    result = {}
    for d in dicts:
        result = deep_merge(result, d)
    return result

def mascarar_dados_sensiveis(texto, campos_sensiveis=None):
    """
    Mascara dados sensíveis em texto/JSON
    """
    if campos_sensiveis is None:
        campos_sensiveis = ['password', 'senha', 'token', 'key', 'secret', 'cpf', 'cnpj']
    
    if isinstance(texto, dict):
        result = {}
        for key, value in texto.items():
            if any(campo in key.lower() for campo in campos_sensiveis):
                result[key] = "***"
            elif isinstance(value, dict):
                result[key] = mascarar_dados_sensiveis(value, campos_sensiveis)
            else:
                result[key] = value
        return result
    
    return texto

# FUNÇÕES DE utils/formatters.py (REAIS)

def formatar_cpf(cpf):
    """
    Formata CPF no padrão XXX.XXX.XXX-XX
    """
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    if len(cpf_limpo) == 11:
        return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
    return cpf_limpo

def formatar_cnpj(cnpj):
    """
    Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX
    """
    cnpj_limpo = re.sub(r'\D', '', str(cnpj))
    if len(cnpj_limpo) == 14:
        return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
    return cnpj_limpo

def formatar_documento(documento):
    """
    Formata CPF ou CNPJ automaticamente
    """
    documento_limpo = re.sub(r'\D', '', str(documento))
    
    if len(documento_limpo) == 11:
        return formatar_cpf(documento_limpo)
    elif len(documento_limpo) == 14:
        return formatar_cnpj(documento_limpo)
    else:
        return documento_limpo

def formatar_telefone(telefone):
    """
    Formata telefone brasileiro
    """
    telefone_limpo = re.sub(r'\D', '', str(telefone))
    
    if len(telefone_limpo) == 10:
        # Telefone fixo: (XX) XXXX-XXXX
        return f"({telefone_limpo[:2]}) {telefone_limpo[2:6]}-{telefone_limpo[6:]}"
    elif len(telefone_limpo) == 11:
        # Celular: (XX) XXXXX-XXXX
        return f"({telefone_limpo[:2]}) {telefone_limpo[2:7]}-{telefone_limpo[7:]}"
    else:
        return telefone_limpo

def formatar_cep(cep):
    """
    Formata CEP no padrão XXXXX-XXX
    """
    cep_limpo = re.sub(r'\D', '', str(cep))
    if len(cep_limpo) == 8:
        return f"{cep_limpo[:5]}-{cep_limpo[5:]}"
    return cep_limpo

def formatar_moeda(valor, simbolo="R$", casas_decimais=2):
    """
    Formata valor monetário brasileiro
    """
    try:
        if isinstance(valor, str):
            # Remove caracteres não numéricos exceto vírgula e ponto
            valor_limpo = re.sub(r'[^\d,.-]', '', valor)
            valor_limpo = valor_limpo.replace(',', '.')
            valor = float(valor_limpo)
        
        valor_formatado = f"{float(valor):,.{casas_decimais}f}"
        valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return f"{simbolo} {valor_formatado}"
    except (ValueError, TypeError):
        return f"{simbolo} 0,00"

def formatar_percentual(valor, casas_decimais=2):
    """
    Formata valor como percentual
    """
    try:
        if isinstance(valor, str):
            valor = float(valor.replace('%', '').replace(',', '.'))
        
        return f"{float(valor):.{casas_decimais}f}%"
    except (ValueError, TypeError):
        return "0,00%"

def formatar_data_brasileira(data, formato_entrada=None):
    """
    Formata data para padrão brasileiro DD/MM/AAAA
    """
    if isinstance(data, str):
        if not formato_entrada:
            # Tenta detectar o formato
            if 'T' in data or 'Z' in data:
                # ISO format
                try:
                    data = datetime.fromisoformat(data.replace('Z', '+00:00'))
                except:
                    return data
            else:
                # Outros formatos
                formatos = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']
                for formato in formatos:
                    try:
                        data = datetime.strptime(data, formato)
                        break
                    except:
                        continue
                else:
                    return data
        else:
            try:
                data = datetime.strptime(data, formato_entrada)
            except:
                return data
    
    if isinstance(data, datetime):
        return data.strftime('%d/%m/%Y')
    
    return str(data)

def formatar_data_hora_brasileira(data, formato_entrada=None):
    """
    Formata data e hora para padrão brasileiro DD/MM/AAAA HH:MM:SS
    """
    if isinstance(data, str):
        if not formato_entrada:
            # Tenta ISO format primeiro
            try:
                data = datetime.fromisoformat(data.replace('Z', '+00:00'))
            except:
                try:
                    data = datetime.strptime(data, '%Y-%m-%d %H:%M:%S')
                except:
                    return data
        else:
            try:
                data = datetime.strptime(data, formato_entrada)
            except:
                return data
    
    if isinstance(data, datetime):
        return data.strftime('%d/%m/%Y %H:%M:%S')
    
    return str(data)

def formatar_nome_proprio(nome):
    """
    Formata nome próprio (primeira letra maiúscula)
    """
    if not nome:
        return ""
    
    # Palavras que devem ficar em minúsculo
    preposicoes = {'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'na', 'no', 'nas', 'nos'}
    
    palavras = nome.lower().split()
    palavras_formatadas = []
    
    for i, palavra in enumerate(palavras):
        if i == 0 or palavra not in preposicoes:
            palavras_formatadas.append(palavra.capitalize())
        else:
            palavras_formatadas.append(palavra)
    
    return ' '.join(palavras_formatadas)

def formatar_endereco(endereco_dict):
    """
    Formata endereço completo
    """
    partes = []
    
    # Logradouro e número
    logradouro = endereco_dict.get('logradouro', '').strip()
    numero = endereco_dict.get('numero', '').strip()
    
    if logradouro:
        if numero:
            partes.append(f"{logradouro}, {numero}")
        else:
            partes.append(logradouro)
    
    # Complemento
    complemento = endereco_dict.get('complemento', '').strip()
    if complemento:
        partes.append(complemento)
    
    # Bairro
    bairro = endereco_dict.get('bairro', '').strip()
    if bairro:
        partes.append(bairro)
    
    # Cidade e estado
    cidade = endereco_dict.get('cidade', '').strip()
    estado = endereco_dict.get('estado', '').strip()
    
    if cidade and estado:
        partes.append(f"{cidade}/{estado}")
    elif cidade:
        partes.append(cidade)
    
    # CEP
    cep = endereco_dict.get('cep', '').strip()
    if cep:
        cep_formatado = formatar_cep(cep)
        partes.append(f"CEP: {cep_formatado}")
    
    return ' - '.join(partes)

def truncar_texto(texto, tamanho_max, sufixo="..."):
    """
    Trunca texto mantendo palavras inteiras
    """
    if not texto or len(texto) <= tamanho_max:
        return texto
    
    texto_truncado = texto[:tamanho_max - len(sufixo)]
    
    # Tenta cortar na última palavra
    ultimo_espaco = texto_truncado.rfind(' ')
    if ultimo_espaco > 0:
        texto_truncado = texto_truncado[:ultimo_espaco]
    
    return texto_truncado + sufixo

def formatar_lista_para_texto(lista, separador=", ", ultimo_separador=" e "):
    """
    Formata lista para texto legível
    Ex: ['A', 'B', 'C'] -> "A, B e C"
    """
    if not lista:
        return ""
    
    if len(lista) == 1:
        return str(lista[0])
    
    if len(lista) == 2:
        return f"{lista[0]}{ultimo_separador}{lista[1]}"
    
    return separador.join(lista[:-1]) + ultimo_separador + str(lista[-1])

def sanitizar_filename(filename):
    """
    Remove caracteres inválidos de nome de arquivo
    """
    if not filename:
        return "arquivo"
    
    # Remove caracteres especiais
    filename_limpo = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Remove espaços extras
    filename_limpo = re.sub(r'\s+', '_', filename_limpo.strip())
    
    # Limita tamanho
    if len(filename_limpo) > 100:
        nome, ext = filename_limpo.rsplit('.', 1) if '.' in filename_limpo else (filename_limpo, '')
        nome = nome[:95]
        filename_limpo = f"{nome}.{ext}" if ext else nome
    
    return filename_limpo or "arquivo"

# FUNÇÕES AUXILIARES E VALIDAÇÃO

def validar_email(email):
    """
    Valida formato de email básico
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ALIASES PARA COMPATIBILIDADE

# Aliases para manter compatibilidade com código existente
formatar_cpf_cnpj = formatar_documento  # Função que escolhe CPF ou CNPJ automaticamente
normalize_text = lambda texto: texto    # Placeholder - se existir uma função real, substituir
format_phone = formatar_telefone
format_cpf_cnpj = formatar_documento
validate_email = validar_email
