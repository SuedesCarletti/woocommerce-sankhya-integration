from datetime import datetime, timedelta, timezone
import calendar

def agora():
    """
    Retorna data/hora atual
    """
    return datetime.now()

def agora_utc():
    """
    Retorna data/hora atual em UTC
    """
    return datetime.now(timezone.utc)

def hoje():
    """
    Retorna data de hoje (sem hora)
    """
    return datetime.now().date()

def ontem():
    """
    Retorna data de ontem
    """
    return (datetime.now() - timedelta(days=1)).date()

def amanha():
    """
    Retorna data de amanhã
    """
    return (datetime.now() + timedelta(days=1)).date()

def inicio_do_mes(data=None):
    """
    Retorna primeiro dia do mês
    """
    if data is None:
        data = datetime.now()
    return data.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def fim_do_mes(data=None):
    """
    Retorna último dia do mês
    """
    if data is None:
        data = datetime.now()
    
    ultimo_dia = calendar.monthrange(data.year, data.month)[1]
    return data.replace(day=ultimo_dia, hour=23, minute=59, second=59, microsecond=999999)

def inicio_do_ano(data=None):
    """
    Retorna primeiro dia do ano
    """
    if data is None:
        data = datetime.now()
    return data.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

def fim_do_ano(data=None):
    """
    Retorna último dia do ano
    """
    if data is None:
        data = datetime.now()
    return data.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)

def parsear_data_brasileira(data_str):
    """
    Converte string de data brasileira para datetime
    """
    if not data_str:
        return None
    
    formatos = [
        '%d/%m/%Y',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%d-%m-%Y',
        '%d-%m-%Y %H:%M:%S',
        '%d-%m-%Y %H:%M'
    ]
    
    for formato in formatos:
        try:
            return datetime.strptime(data_str.strip(), formato)
        except ValueError:
            continue
    
    # Tenta ISO format
    try:
        return datetime.fromisoformat(data_str.replace('Z', '+00:00'))
    except:
        pass
    
    raise ValueError(f"Formato de data não reconhecido: {data_str}")

def parsear_data_sankhya(data_str):
    """
    Converte string de data do Sankhya para datetime
    Sankhya usa formato DD/MM/AAAA
    """
    if not data_str:
        return None
    
    try:
        return datetime.strptime(data_str.strip(), '%d/%m/%Y')
    except ValueError:
        return parsear_data_brasileira(data_str)

def data_para_sankhya(data):
    """
    Converte datetime para formato Sankhya (DD/MM/AAAA)
    """
    if data is None:
        return ""
    
    if isinstance(data, str):
        data = parsear_data_brasileira(data)
    
    return data.strftime('%d/%m/%Y')

def parsear_data_woocommerce(data_str):
    """
    Converte string de data do WooCommerce para datetime
    WooCommerce usa ISO format
    """
    if not data_str:
        return None
    
    try:
        # Remove 'Z' e adiciona timezone info
        if data_str.endswith('Z'):
            data_str = data_str[:-1] + '+00:00'
        
        return datetime.fromisoformat(data_str)
    except ValueError:
        return parsear_data_brasileira(data_str)

def idade_em_anos(data_nascimento):
    """
    Calcula idade em anos
    """
    if isinstance(data_nascimento, str):
        data_nascimento = parsear_data_brasileira(data_nascimento)
    
    hoje = datetime.now().date()
    if isinstance(data_nascimento, datetime):
        data_nascimento = data_nascimento.date()
    
    idade = hoje.year - data_nascimento.year
    
    # Ajusta se ainda não fez aniversário este ano
    if hoje < data_nascimento.replace(year=hoje.year):
        idade -= 1
    
    return idade

def diferenca_em_dias(data1, data2):
    """
    Calcula diferença em dias entre duas datas
    """
    if isinstance(data1, str):
        data1 = parsear_data_brasileira(data1)
    if isinstance(data2, str):
        data2 = parsear_data_brasileira(data2)
    
    return abs((data2 - data1).days)

def eh_dia_util(data):
    """
    Verifica se é dia útil (segunda a sexta)
    """
    if isinstance(data, str):
        data = parsear_data_brasileira(data)
    
    return data.weekday() < 5  # 0-6, onde 0=segunda, 6=domingo

def proximo_dia_util(data=None):
    """
    Retorna próximo dia útil
    """
    if data is None:
        data = datetime.now()
    elif isinstance(data, str):
        data = parsear_data_brasileira(data)
    
    while not eh_dia_util(data):
        data += timedelta(days=1)
    
    return data

def eh_fim_de_semana(data):
    """
    Verifica se é fim de semana
    """
    if isinstance(data, str):
        data = parsear_data_brasileira(data)
    
    return data.weekday() >= 5  # 5=sábado, 6=domingo

def nome_do_mes(numero_mes):
    """
    Retorna nome do mês em português
    """
    meses = [
        '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    
    if 1 <= numero_mes <= 12:
        return meses[numero_mes]
    return ''

def nome_do_dia_semana(data):
    """
    Retorna nome do dia da semana em português
    """
    if isinstance(data, str):
        data = parsear_data_brasileira(data)
    
    dias = [
        'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
        'Sexta-feira', 'Sábado', 'Domingo'
    ]
    
    return dias[data.weekday()]

def tempo_relativo(data):
    """
    Retorna descrição relativa do tempo (ex: "há 2 horas", "em 3 dias")
    """
    if isinstance(data, str):
        data = parsear_data_brasileira(data)
    
    agora = datetime.now()
    if data.tzinfo is None and agora.tzinfo is None:
        diferenca = agora - data
    else:
        # Normaliza timezone
        if data.tzinfo is None:
            data = data.replace(tzinfo=timezone.utc)
        if agora.tzinfo is None:
            agora = agora.replace(tzinfo=timezone.utc)
        diferenca = agora - data
    
    segundos = diferenca.total_seconds()
    
    if segundos < 0:
        # Data no futuro
        segundos = abs(segundos)
        prefixo = "em"
    else:
        # Data no passado
        prefixo = "há"
    
    if segundos < 60:
        return f"{prefixo} alguns segundos"
    elif segundos < 3600:
        minutos = int(segundos / 60)
        return f"{prefixo} {minutos} minuto{'s' if minutos != 1 else ''}"
    elif segundos < 86400:
        horas = int(segundos / 3600)
        return f"{prefixo} {horas} hora{'s' if horas != 1 else ''}"
    elif segundos < 2592000:  # 30 dias
        dias = int(segundos / 86400)
        return f"{prefixo} {dias} dia{'s' if dias != 1 else ''}"
    elif segundos < 31536000:  # 1 ano
        meses = int(segundos / 2592000)
        return f"{prefixo} {meses} mês{'es' if meses != 1 else ''}"
    else:
        anos = int(segundos / 31536000)
        return f"{prefixo} {anos} ano{'s' if anos != 1 else ''}"

def timestamp_para_data(timestamp):
    """
    Converte timestamp Unix para datetime
    """
    try:
        return datetime.fromtimestamp(float(timestamp))
    except (ValueError, TypeError):
        return None

def data_para_timestamp(data):
    """
    Converte datetime para timestamp Unix
    """
    if isinstance(data, str):
        data = parsear_data_brasileira(data)
    
    return int(data.timestamp())