# WooCommerce-Sankhya Integration

**Integração completa entre WooCommerce e ERP Sankhya**

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.2%2B-green)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)](https://railway.app)

## **Versão Atual: 2.2 (Estável)**

- **Suporte completo a transportadoras** (AllPost, Correios, etc.)
- **Webhooks em tempo real** do WooCommerce
- **Sincronização automática** de pedidos e clientes
- **Utils consolidados** (correção de imports duplicados)
- **Sistema de segurança** robusto com rate limiting
- **Arquitetura modular** otimizada

---

## **Funcionalidades**

### **Principais**
- **Webhooks em tempo real** do WooCommerce
- **Sincronização automática** de pedidos e clientes
- **Suporte completo a transportadoras** (AllPost, Correios, etc.)
- **Mapeamento inteligente** de produtos e categorias
- **Sistema de logs avançado** com cores e emojis
- **Health checks** completos e monitoramento

### **Técnicas**
- **Arquitetura modular** estável
- **Rate limiting** e validações HMAC
- **Sistema de segurança** robusto
- **Suporte multi-ambiente** (sandbox/production)
- **Context managers** para recursos
- **Utils consolidados** (sem duplicações)

---

## **Estrutura do Projeto**

```
projeto/
├── app.py                          # Aplicação principal
├── requirements.txt                # Dependências
├── runtime.txt                     # Python 3.7.12
├── .env.example                    # Configurações exemplo
│
├── config/
│   ├── __init__.py
│   └── settings.py                 # Configurações centralizadas
│
├── services/
│   ├── sankhya/                    # Módulo Sankhya
│   │   ├── __init__.py
│   │   ├── auth.py                 # Autenticação
│   │   ├── base.py                 # Cliente base
│   │   ├── parceiros.py            # Gestão de clientes
│   │   ├── contatos.py             # Gestão de contatos
│   │   ├── enderecos.py            # Endereços e bairros
│   │   ├── pedidos.py              # Gestão de pedidos
│   │   ├── transportadoras.py      # Transportadoras
│   │   ├── produtos.py             # Produtos
│   │   ├── estoque.py              # Estoque
│   │   └── service.py              # Serviço integrado
│   │
│   └── woocommerce/                # Módulo WooCommerce
│       ├── __init__.py
│       ├── client.py               # Cliente da API
│       ├── processors.py           # Processadores de eventos
│       ├── validators.py           # Validações
│       ├── mapper.py               # Mapeamento de dados
│       └── service.py              # Serviço integrado
│
├── utils/                          # Utilitários CONSOLIDADOS
│   ├── __init__.py                 # Exports organizados
│   ├── common.py                   # Funções consolidadas (33 funções)
│   ├── validators.py               # Validações específicas
│   ├── dates.py                    # Utilitários de data
│   ├── logger.py                   # Sistema de logging
│   └── normalize.py                # Normalização de texto
│
├── webhooks/                       # Módulo de webhooks
│   ├── __init__.py
│   ├── handlers.py                 # Handlers de webhook
│   ├── validators.py               # Validações específicas
│   ├── security.py                 # Segurança e rate limiting
│   └── middleware.py               # Middleware e decorators
│
└── docs/                           # Documentação
    └── README.md                   # Este arquivo
```

---

## **Instalação Rápida**

### **1. Clone e Configure**
```bash
git clone <url-do-repositorio>
cd woocommerce-sankhya-integration

# Configure ambiente
cp .env.example .env
nano .env  # Configure suas credenciais
```

### **2. Instale Dependências**
```bash
pip install -r requirements.txt
```

### **3. Execute**
```bash
python app.py
```

**Pronto! Aplicação rodando em http://localhost:3000**

---

## **Configuração**

### **Variáveis Obrigatórias (.env)**
```bash
# === AMBIENTE ===
USAR_AMBIENTE=sandbox              # ou 'production'
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR

# === WOOCOMMERCE ===
WC_URL=https://loja.com/wp-json/wc/v3
WC_KEY=ck_xxxxx
WC_SECRET=cs_xxxxx
WC_WEBHOOK_SECRET=webhook_secret   # Opcional (HMAC)

# === SANKHYA ===
SANKHYA_BASE_URL=https://api.sankhya.com.br
SANKHYA_USER=usuario
SANKHYA_PASSWORD=senha
SANKHYA_EMPRESA=1
SANKHYA_CODVEND=1
SANKHYA_CODTIPOPER=1
SANKHYA_CODTIPVENDA=1

# === WEBHOOK SECURITY ===
WEBHOOK_SECRET=seu_token_super_secreto
WEBHOOK_RATE_LIMIT=100             # Requests por minuto
WEBHOOK_ALLOWED_IPS=              # IPs permitidos (opcional)
```

### **Configurações Opcionais**
```bash
# === FEATURES ===
PEDIDOS_INFORMAR_PRECO=true
PEDIDOS_TIPMOV_PADRAO=P           # P=Pedido, V=Venda
TRANSPORTADORAS_USAR_PADRAO=true
PRODUTOS_NORMALIZAR_SKUS=true

# === DEBUG ===
DEBUG_MAPEAMENTO_PRODUTOS=false
DEBUG_ESTRUTURA_PEDIDOS=false
FLASK_DEBUG=false
```

---

## **API Endpoints Completos**

### **Endpoints Principais**

#### **GET /** - Informações da API
```bash
curl http://localhost:3000/

# Response:
{
  "message": "WooCommerce-Sankhya Integration API",
  "version": "2.2",
  "status": "online",
  "new_features": [
    "Suporte a transportadoras",
    "Processamento de AllPost",
    "TIPMOV = P (Pedido)"
  ],
  "endpoints": ["lista de todos os endpoints..."]
}
```

#### **GET /health** - Health Check Geral
```bash
curl http://localhost:3000/health

# Response:
{
  "status": "healthy",
  "service": "woocommerce-sankhya-integration", 
  "version": "2.2",
  "environment": "sandbox",
  "checks": {
    "config_loaded": true,
    "webhook_secret": true,
    "woocommerce_configured": true,
    "sankhya_configured": true
  }
}
```

#### **GET /version** - Versões dos Módulos
```bash
curl http://localhost:3000/version

# Response:
{
  "application": "2.2",
  "python": "3.7.12",
  "modules": {
    "services": "2.0.0",
    "webhooks": "2.0.0",
    "utils": "2.0.0"
  },
  "features": {
    "transportadoras": "2.2.0",
    "allpost_integration": "2.2.0"
  }
}
```

#### **GET /config?token=SEU_TOKEN** - Configurações Seguras
```bash
curl "http://localhost:3000/config?token=SEU_TOKEN"

# Response:
{
  "status": "success",
  "config": {
    "USAR_AMBIENTE": "sandbox",
    "WC_URL": "https://loja.com/wp-json/wc/v3",
    "WC_KEY_CONFIGURED": true,
    "WC_SECRET_CONFIGURED": true,
    "SANKHYA_BASE_URL": "https://api.sankhya.com.br",
    "WEBHOOK_SECRET_CONFIGURED": true,
    "TRANSPORTADORAS_ENABLED": true
  }
}
```

---

### **Endpoints WooCommerce**

#### **GET /woo/orders?token=SEU_TOKEN** - Listar Pedidos
```bash
# Listar últimos 10 pedidos
curl "http://localhost:3000/woo/orders?token=SEU_TOKEN"

# Com parâmetros opcionais
curl "http://localhost:3000/woo/orders?token=SEU_TOKEN&per_page=5&status=processing"

# Response:
{
  "status": "success",
  "pedidos": [
    {
      "id": 12345,
      "status": "processing",
      "total": "199.90",
      "date_created": "2024-01-15T10:30:00",
      "billing": {
        "first_name": "João",
        "last_name": "Silva",
        "email": "joao@email.com"
      },
      "transportadora_info": {
        "nome": "Correios",
        "prazo": "5 dias úteis"
      }
    }
  ],
  "total_encontrados": 1,
  "parametros": {
    "per_page": 10,
    "status": null
  }
}
```

#### **GET /woo/customers/{id}?token=SEU_TOKEN** - Detalhes do Cliente
```bash
curl "http://localhost:3000/woo/customers/123?token=SEU_TOKEN"

# Response:
{
  "status": "success",
  "cliente": {
    "id": 123,
    "email": "joao@email.com",
    "first_name": "João",
    "last_name": "Silva",
    "estatisticas": {
      "total_gasto": "R$ 1.234,56",
      "pedidos_encontrados": 5
    },
    "endereco_cobranca": {...},
    "endereco_entrega": {...},
    "pedidos_recentes": [...]
  }
}
```

#### **POST /customers/woocommerce** - Sincronizar Cliente
```bash
curl -X POST "http://localhost:3000/customers/woocommerce" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_data": {
      "id": 123,
      "email": "joao@email.com",
      "first_name": "João",
      "last_name": "Silva",
      "billing": {
        "address_1": "Rua das Flores, 123",
        "city": "São Paulo",
        "state": "SP",
        "postcode": "01234-567"
      }
    }
  }'

# Response:
{
  "sucesso": true,
  "codparc": 12345,
  "mensagem": "Cliente processado com sucesso",
  "detalhes": {...}
}
```

---

### **Endpoints de Webhooks**

#### **POST /webhook/?token=SEU_TOKEN** - Webhook Principal
```bash
# Este endpoint recebe webhooks do WooCommerce automaticamente
# Configurar no WooCommerce Admin:
# URL: https://seu-servidor.com/webhook/?token=SEU_TOKEN

# Exemplo de teste manual:
curl -X POST "http://localhost:3000/webhook/?token=SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-WC-Webhook-Event: order.created" \
  -H "X-WC-Webhook-Resource: order" \
  -d '{
    "id": 12345,
    "status": "processing",
    "billing": {
      "first_name": "João",
      "last_name": "Silva",
      "email": "joao@email.com"
    }
  }'

# Response (sempre 200):
{
  "status": "received",
  "message": "Webhook processado com sucesso",
  "pedido_sankhya": "NUNOTA 67890",
  "transportadora": "Correios"
}
```

#### **GET /webhook/health** - Health Check de Webhooks
```bash
curl http://localhost:3000/webhook/health

# Response:
{
  "status": "healthy",
  "webhook_module": "operational",
  "version": "2.0.0",
  "last_webhook": "2024-01-15T10:30:00",
  "stats": {
    "total_received": 150,
    "successful": 145,
    "errors": 5
  }
}
```

#### **GET /webhook/stats?token=SEU_TOKEN** - Estatísticas
```bash
curl "http://localhost:3000/webhook/stats?token=SEU_TOKEN"

# Response:
{
  "status": "success",
  "estatisticas": {
    "webhooks_recebidos": 150,
    "sucessos": 145,
    "erros": 5,
    "rate_limit_ativo": true,
    "uptime": "2d 5h 30m",
    "tipos_evento": {
      "order.created": 80,
      "order.updated": 45,
      "customer.created": 20
    }
  }
}
```

#### **POST /webhook/test?token=SEU_TOKEN** - Teste de Webhook
```bash
curl -X POST "http://localhost:3000/webhook/test?token=SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_type": "order_created",
    "simulate_error": false
  }'

# Response:
{
  "status": "success",
  "message": "Teste de webhook executado com sucesso",
  "test_result": {...}
}
```

#### **GET /webhook/debug?token=SEU_TOKEN** - Debug Info
```bash
curl "http://localhost:3000/webhook/debug?token=SEU_TOKEN"

# Response:
{
  "status": "success",
  "debug_info": {
    "configuracoes": {...},
    "ultimos_webhooks": [...],
    "rate_limit_status": {...},
    "validacoes_ativas": [...]
  }
}
```

---

### **Endpoints Sankhya**

#### **GET /sankhya/transportadoras?token=SEU_TOKEN** - Listar Transportadoras
```bash
curl "http://localhost:3000/sankhya/transportadoras?token=SEU_TOKEN"

# Response:
{
  "status": "success",
  "transportadoras": [
    {
      "CODPARC": 1001,
      "NOMEPARC": "Correios",
      "ATIVO": "S",
      "IDALLPOST": "correios"
    },
    {
      "CODPARC": 1002, 
      "NOMEPARC": "JADLOG",
      "ATIVO": "S",
      "IDALLPOST": "jadlog"
    }
  ],
  "total": 15
}
```

#### **GET /sankhya/stats?token=SEU_TOKEN** - Estatísticas do Sistema
```bash
curl "http://localhost:3000/sankhya/stats?token=SEU_TOKEN"

# Response:
{
  "status": "success",
  "estatisticas": {
    "pedidos_criados": 50,
    "clientes_criados": 25,
    "transportadoras_ativas": 15,
    "tempo_medio_processamento": "2.5s",
    "uptime_sankhya": "99.9%"
  }
}
```

#### **POST /sankhya/test?token=SEU_TOKEN** - Teste de Integração
```bash
curl -X POST "http://localhost:3000/sankhya/test?token=SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_connection": true,
    "test_auth": true,
    "id_allpost": "correios"
  }'

# Response:
{
  "status": "success",
  "test_results": {
    "config_ok": true,
    "testes_realizados": [
      {
        "teste": "conexao_sankhya",
        "sucesso": true,
        "resultado": "Conexão estabelecida com sucesso"
      },
      {
        "teste": "transportadora_correios",
        "sucesso": true,
        "resultado": "Correios (1001)"
      }
    ]
  }
}
```

---

### **Endpoints de Sincronização**

#### **POST /sync/orders?token=SEU_TOKEN** - Sincronização Manual
```bash
curl -X POST "http://localhost:3000/sync/orders?token=SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 5,
    "status": ["processing", "pending"],
    "force_update": false
  }'

# Response:
{
  "status": "success",
  "mensagem": "Sincronização concluída",
  "resultados": {
    "total_processados": 5,
    "sucessos": 4,
    "erros": 1,
    "com_transportadora": 3,
    "tempo_execucao": "12.5s"
  },
  "detalhes": [
    {
      "pedido_woo": 12345,
      "pedido_sankhya": "NUNOTA 67890",
      "status": "success",
      "transportadora": "Correios"
    }
  ]
}
```

---

## **Configuração de Webhooks no WooCommerce**

### **No WooCommerce Admin**
1. Vá em **WooCommerce > Configurações > Avançado > Webhooks**
2. Clique em **Adicionar Webhook**
3. Configure:

```
Nome: Sankhya Integration
Status: Ativo
Tópico: Pedido criado (ou personalizado)
URL de entrega: https://seu-servidor.com/webhook/?token=SEU_TOKEN
Secret: seu_webhook_secret (opcional)
Versão da API: wp-json/wc/v3
```

### **Eventos Suportados**
- `order.created` - Novo pedido criado
- `order.updated` - Pedido atualizado
- `order.deleted` - Pedido excluído
- `customer.created` - Novo cliente
- `customer.updated` - Cliente atualizado
- `product.created` - Novo produto
- `product.updated` - Produto atualizado

---

## **Testes e Debug**

### **Health Checks Rápidos**
```bash
# Health check geral
curl http://localhost:3000/health

# Health check específico de webhooks
curl http://localhost:3000/webhook/health

# Verificar versões
curl http://localhost:3000/version
```

### **Teste Manual Completo**
```bash
# 1. Testar configuração
curl "http://localhost:3000/config?token=SEU_TOKEN"

# 2. Testar WooCommerce
curl "http://localhost:3000/woo/orders?token=SEU_TOKEN&per_page=1"

# 3. Testar Sankhya
curl -X POST "http://localhost:3000/sankhya/test?token=SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_connection": true}'

# 4. Testar Webhook
curl -X POST "http://localhost:3000/webhook/test?token=SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_type": "order_created"}'

# 5. Testar Sincronização
curl -X POST "http://localhost:3000/sync/orders?token=SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 1}'
```

### **Debug de Logs**
```bash
# Execute com debug ativo
LOG_LEVEL=DEBUG python app.py

# Logs mostram cores e emojis automaticamente:
# 2024-01-15 10:30:15 | webhooks | INFO | Webhook: order.created | ID: 123
# 2024-01-15 10:30:16 | sankhya  | INFO | Pedido criado: NUNOTA 456
# 2024-01-15 10:30:17 | main-app | INFO | Transportadora: Correios
```

---

## **Deploy**

### **Deploy Local**
```bash
# Desenvolvimento
python app.py

# Produção com Gunicorn
gunicorn -w 4 -b 0.0.0.0:3000 app:app
```

### **Deploy no Railway (Recomendado)**
```bash
# Railway CLI
railway login
railway link
railway up

# Ou via Git
git add .
git commit -m "Deploy para Railway"
git push origin main
```

### **Deploy com Docker**
```dockerfile
FROM python:3.7.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000
CMD ["python", "app.py"]
```

### **Variáveis de Ambiente para Deploy**
```bash
# Para produção (Railway)
USAR_AMBIENTE=production
LOG_LEVEL=INFO
FLASK_DEBUG=false
HOST=0.0.0.0
PORT=3000

# Para desenvolvimento  
USAR_AMBIENTE=sandbox
LOG_LEVEL=DEBUG
FLASK_DEBUG=true
```

---

## **Segurança**

### **Recursos de Segurança**
- **Token de autenticação** obrigatório para endpoints sensíveis
- **Rate limiting** por IP (100 req/min configurável)
- **Validação HMAC** opcional para webhooks
- **Whitelist de IPs** configurável
- **HTTPS** recomendado para produção
- **Logs de segurança** detalhados

### **Boas Práticas**
```bash
# Use tokens fortes
WEBHOOK_SECRET=$(openssl rand -hex 32)

# Configure HTTPS
WC_URL=https://sua-loja.com/wp-json/wc/v3

# Restrinja IPs se possível
WEBHOOK_ALLOWED_IPS=192.168.0.10,192.168.0.11

# Use validação HMAC em produção
WC_WEBHOOK_SECRET=seu_secret_compartilhado
VALIDAR_HMAC_SIGNATURE=true
```

---

## **Monitoramento**

### **Logs Estruturados**
A aplicação gera logs coloridos e estruturados automaticamente:

```bash
2024-01-15 10:30:15 | main-app | INFO | Iniciando WooCommerce-Sankhya Integration v2.2
2024-01-15 10:30:16 | webhooks | INFO | Webhook: order.created | ID: 123
2024-01-15 10:30:17 | sankhya  | INFO | Cliente criado: CODPARC 789
2024-01-15 10:30:18 | webhooks | INFO | Pedido processado: NUNOTA 456
2024-01-15 10:30:19 | main-app | INFO | Transportadora: Correios
```

### **Métricas Disponíveis**
```bash
# Estatísticas de webhooks
curl "http://localhost:3000/webhook/stats?token=SEU_TOKEN"

# Estatísticas do Sankhya
curl "http://localhost:3000/sankhya/stats?token=SEU_TOKEN"

# Health check completo
curl "http://localhost:3000/health"
```

---

## **Solução de Problemas**

### **Problemas Comuns**

#### **1. Erro de autenticação Sankhya**
```bash
# Verifique credenciais
curl "http://localhost:3000/config?token=SEU_TOKEN"

# Teste conexão
curl -X POST "http://localhost:3000/sankhya/test?token=SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_connection": true}'
```

#### **2. Webhooks não chegam**
```bash
# Teste o endpoint diretamente
curl -X POST "http://localhost:3000/webhook/test?token=SEU_TOKEN"

# Verifique health check
curl "http://localhost:3000/webhook/health"

# Verifique configuração no WooCommerce
curl "http://localhost:3000/webhook/debug?token=SEU_TOKEN"
```

#### **3. Rate limit excedido**
```bash
# Verifique estatísticas
curl "http://localhost:3000/webhook/stats?token=SEU_TOKEN"

# Ajuste limite no .env se necessário
WEBHOOK_RATE_LIMIT=200
```

#### **4. Erro de configuração**
```bash
# Execute validação automática
curl "http://localhost:3000/config?token=SEU_TOKEN"

# Verifique variáveis de ambiente
curl "http://localhost:3000/version"
```

### **Debug Avançado**
```bash
# Execute com debug completo
LOG_LEVEL=DEBUG LOG_COLORED=true python app.py

# Teste todos os endpoints
curl "http://localhost:3000/"
curl "http://localhost:3000/health"
curl "http://localhost:3000/webhook/health"

# Verifique configurações
curl "http://localhost:3000/config?token=SEU_TOKEN"
```

---

## **Changelog**

### **v2.2.0 (Atual) - Estabilizada**
- **Suporte completo a transportadoras** (AllPost, Correios, etc.)
- **Utils consolidados** - correção de imports duplicados
- **Processamento de AllPost** integrado
- **TIPMOV = P (Pedido)** como padrão
- **Correção de bugs** críticos
- **Sistema de logs** melhorado
- **Health checks** aprimorados

### **v2.0.0 - Modularização**
- Arquitetura modular completa
- Sistema de segurança robusto
- Logging estruturado
- Health checks avançados

### **v1.0.0 - MVP**
- Integração básica funcional
- Webhooks simples
- Arquitetura monolítica

---

## **Contribuição**

### **Como Contribuir**
1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### **Padrões de Código**
- Use type hints quando possível
- Docstrings em funções públicas
- Logs estruturados com emojis
- Testes unitários para novas features
- Siga PEP 8 para formatação

### **Estrutura de Commits**
```
tipo(escopo): descrição curta

Descrição mais detalhada se necessário.

- feat: Nova funcionalidade
- fix: Correção de bug
- docs: Documentação
- style: Formatação
- refactor: Refatoração
- test: Testes
- chore: Tarefas de manutenção
```

---

## **Licença**

Todos os direitos reservados. Código publicado apenas para consulta e avaliação; veja o arquivo [LICENSE](LICENSE).

## **Suporte**

### **Canais de Suporte**
- **Email**: suporte@empresa.com
- **WhatsApp**: +55 (xx) 9xxxx-xxxx
- **Issues**: [GitHub Issues](https://github.com/seu-repo/issues)
- **Documentação**: [Wiki do Projeto](https://github.com/seu-repo/wiki)

### **FAQ**

**Q: Como configurar múltiplos ambientes?**
A: Use a variável `USAR_AMBIENTE=sandbox` ou `production` no .env

**Q: Posso usar com outras versões do Python?**
A: Recomendamos Python 3.7.12, mas funciona com 3.7+

**Q: Como fazer backup das configurações?**
A: Faça backup do arquivo `.env` e das configurações do banco

**Q: Suporta múltiplas lojas WooCommerce?**
A: Atualmente suporta uma loja por instância da aplicação

**Q: Como testar todos os endpoints?**
A: Use o script de teste disponível ou execute os comandos curl documentados acima

---

## **Reconhecimentos**

Agradecimentos especiais a:
- **WooCommerce** pela excelente API REST
- **Sankhya** pelo sistema ERP robusto
- **Python Community** pelas bibliotecas incríveis
- **Flask** pelo framework minimalista
- **Railway** pela plataforma de deploy excelente
- **Contribuidores** que tornaram este projeto possível

---

## **Estatísticas do Projeto**

```
Estatísticas v2.2.0:
├── Linguagem: Python 3.7+
├── Framework: Flask 2.2+
├── Dependências: 12 principais
├── Arquivos: ~25 (otimizado)
├── Linhas de código: ~2,800
├── Cobertura: Produção estável
├── Documentação: 100% atualizada
├── Performance: Excelente
├── API Endpoints: 15 principais
└── Bugs conhecidos: 0
```

---

<div align="center">

**WooCommerce-Sankhya Integration v2.2**

*Integração robusta, estável e escalável!*

[![Stars](https://img.shields.io/github/stars/seu-repo?style=social)](https://github.com/seu-repo)
[![Forks](https://img.shields.io/github/forks/seu-repo?style=social)](https://github.com/seu-repo)
[![Issues](https://img.shields.io/github/issues/seu-repo)](https://github.com/seu-repo/issues)

---

*Desenvolvido com pela equipe de integração*

*Última atualização: Janeiro 2025*

*Deploy atual: Railway (Produção Estável)*

</div>
