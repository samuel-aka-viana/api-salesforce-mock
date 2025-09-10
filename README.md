# Salesforce Marketing Cloud API Clone

Uma implementação que simula a API REST do Salesforce Marketing Cloud, com endpoints compatíveis para desenvolvimento, testes e integração de sistemas de marketing digital.

## Visão Geral

Permite testar integrações, prototipar soluções e desenvolver aplicações sem depender do ambiente de produção da Salesforce. Inclui autenticação JWT, rate limiting, validação de dados e documentação OpenAPI.

## Características Principais

### Funcionalidades da API

* Autenticação JWT: tokens de acesso e refresh tokens.
* Gerenciamento de Contatos: CRUD, busca avançada, operações em lote.
* Campanhas de Marketing: criação, execução e estatísticas.
* Definições de Email: templates, envio, personalização.
* Eventos de Dados: tracking de interações e análise de funil.
* Gerenciamento de Assets: upload, download e organização.

### Características Técnicas

* Rate limiting configurável por endpoint.
* Paginação automática em todas as listagens.
* Validação rigorosa de dados de entrada.
* Logging estruturado para auditoria.
* Documentação OpenAPI/Swagger integrada.
* Suporte a múltiplos formatos de resposta.

## Arquitetura

### Stack Tecnológico

* Backend: Flask 3.1+ com extensões.
* Banco de Dados: PostgreSQL 17 com extensões de busca textual.
* Cache/Session: Redis 7 para rate limiting e sessões.
* ORM: SQLAlchemy 2.0 + Alembic.
* Containerização: Docker Compose.

### Componentes Principais

```text
├── app.py                 # Aplicação Flask principal
├── auth/                  # Sistema de autenticação JWT
├── salesforce_api/        # Endpoints da API simulada
│   ├── contacts.py        # Gerenciamento de contatos
│   ├── campaigns.py       # Campanhas de marketing
│   ├── email_definitions.py # Templates de email
│   ├── data_events.py     # Eventos e analytics
│   └── assets.py          # Gerenciamento de arquivos
├── models/                # Modelos de dados SQLAlchemy
├── docs/                  # Schemas e documentação
└── utils/                 # Utilitários e população de dados
```

## Instalação e Configuração

### Pré-requisitos

* Docker 20.10+
* Docker Compose 2.0+
* Make (opcional)

### Configuração Rápida

Clone o repositório:

```bash
git clone <repository-url>
cd salesforce-marketing-cloud-api
```

Configure as variáveis de ambiente:

```bash
cp .env.example .env
# Edite o arquivo .env conforme necessário
```

Inicie o ambiente de desenvolvimento:

```bash
make quick-start
# ou manualmente:
# docker-compose build
# docker-compose up -d
# make populate
```

Verifique a instalação:

```bash
curl http://localhost:5000/health
```

### Variáveis de Ambiente Principais

```env
# Banco de Dados
POSTGRES_DB=marketing_cloud_db
POSTGRES_USER=marketing_user
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_PASSWORD=redis_password

# Aplicação
SECRET_KEY=your-secret-key
JWT_SECRET=jwt-secret-key
API_PORT=5000

# Desenvolvimento
FLASK_ENV=development
POPULATE_INITIAL_DATA=true
```

## Uso da API

### Autenticação

Todas as operações requerem JWT. Primeiro obtenha um access token:

```bash
curl -X POST http://localhost:5000/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "marketing_cloud_app_1",
    "client_secret": "super_secret_key_123",
    "grant_type": "client_credentials"
  }'
```

### Clientes Pré-configurados

| Cliente                  | Permissões      | Descrição           |
| ------------------------ | --------------- | ------------------- |
| marketing\_cloud\_app\_1 | Completas       | Aplicação principal |
| analytics\_dashboard     | Somente leitura | Dashboard analítico |
| mobile\_app\_client      | Limitadas       | Aplicação móvel     |

---

### Endpoints Principais

#### Contatos

Listar:

```bash
GET /contacts/v1/contacts?page=1&per_page=50
```

Criar:

```bash
POST /contacts/v1/contacts
Content-Type: application/json

{
  "emailAddress": "user@example.com",
  "firstName": "João",
  "lastName": "Silva",
  "status": "Active"
}
```

Busca avançada:

```bash
POST /contacts/v1/contacts/search
Content-Type: application/json

{
  "criteria": {
    "searchTerm": "joão",
    "status": ["Active"],
    "location": {"cities": ["São Paulo"]}
  }
}
```

#### Campanhas

Criar:

```bash
POST /campaigns/v1/campaigns
Content-Type: application/json

{
  "name": "Black Friday 2024",
  "campaignType": "Email",
  "subjectLine": "Ofertas Especiais!",
  "fromEmail": "marketing@empresa.com"
}
```

Iniciar:

```bash
POST /campaigns/v1/campaigns/{campaignId}/start
```

Estatísticas:

```bash
GET /campaigns/v1/campaigns/{campaignId}/statistics
```

#### Eventos de Dados

Registrar evento:

```bash
POST /data/v1/events
Content-Type: application/json

{
  "eventType": "EmailOpen",
  "contactKey": "contact_123",
  "campaignId": "campaign_456",
  "eventData": {
    "userAgent": "Mozilla/5.0...",
    "ipAddress": "192.168.1.1"
  }
}
```

Análise de funil:

```bash
POST /data/v1/events/funnel
Content-Type: application/json

{
  "steps": [
    {"eventType": "EmailOpen", "name": "Email Aberto"},
    {"eventType": "EmailClick", "name": "Link Clicado"},
    {"eventType": "Purchase", "name": "Compra Realizada"}
  ]
}
```

#### Documentação da API

* Swagger UI: `http://localhost:5000/docs/`
* Endpoint de informações: `http://localhost:5000/v1`

## Rate Limiting

| Categoria    | Limite                        |
| ------------ | ----------------------------- |
| Padrão       | 1000 req/hora, 100 req/minuto |
| Autenticação | 5 req/segundo                 |
| Uploads      | 50 req/hora                   |

## Códigos de Resposta

| Código | Significado            |
| -----: | ---------------------- |
|    200 | Sucesso                |
|    201 | Criado                 |
|    400 | Dados inválidos        |
|    401 | Não autenticado        |
|    403 | Sem permissão          |
|    404 | Recurso não encontrado |
|    429 | Rate limit excedido    |
|    500 | Erro interno           |

## Desenvolvimento

### Comandos Make

```bash
# Desenvolvimento
make up-dev          # Iniciar em modo desenvolvimento
make logs            # Visualizar logs
make shell           # Acesso ao container da aplicação
make test            # Executar testes

# Banco de Dados
make populate        # Popular com dados de exemplo
make backup          # Backup do banco
make migrate         # Executar migrações

# Manutenção
make clean           # Limpar containers e imagens
make reset           # Reset completo do ambiente
```

### Estrutura de Testes

```bash
# Suite completa
make test

# Coverage
make test-coverage

# Qualidade
make lint
make format
```

## População de Dados

```bash
# População automática
make populate

# População forçada (limpa dados existentes)
make populate-force

# Dados customizados
docker-compose exec api python populate_data.py
```

## Monitoramento

* Health Check: `http://localhost:5000/health`
* PgAdmin: `http://localhost:8080` ([dev@example.com](mailto:dev@example.com) / admin)
* Redis Commander: `http://localhost:8081`
* Logs: `make logs` ou `docker-compose logs -f`

## Produção

### Deploy com Docker

```bash
# Build para produção
make build

# Deploy
make deploy

# Com proxy Nginx
make up-prod
```

### Configurações de Produção

* Configurar HTTPS com certificados SSL.
* Ajustar variáveis de ambiente de produção.
* Configurar backup automatizado.
* Monitorar com Prometheus/Grafana.

## Troubleshooting

### Problemas Comuns

Erro de conexão com banco:

```bash
make down
make up
make health
```

Rate limit excedido:

```bash
# Verificar Redis
make shell-redis
# No Redis:
FLUSHALL
```

Dados corrompidos:

```bash
make reset
make populate
```

## Contribuição

### Fluxo de Desenvolvimento

```bash
# Criar branch
git checkout -b feature/nova-funcionalidade

# Verificações locais
make lint && make test
```

1. Faça fork do repositório.
2. Implemente com testes.
3. Commits seguindo convenções.
4. Abra um Pull Request.
