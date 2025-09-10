.PHONY: help build up down restart logs status clean populate test shell backup restore

COMPOSE_FILE = docker-compose.yml
PROJECT_NAME = marketing_cloud
BACKUP_DIR = ./backups

GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
BLUE = \033[0;34m
NC = \033[0m # No Color

.DEFAULT_GOAL := help

help:
	@echo "$(GREEN)Marketing Cloud API - Comandos Disponíveis$(NC)"
	@echo "=================================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(BLUE)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build:
	@echo "$(YELLOW)🔨 Construindo imagens Docker...$(NC)"
	docker-compose -f $(COMPOSE_FILE) build --no-cache

build-dev:
	@echo "$(YELLOW)🔨 Construindo imagem da aplicação...$(NC)"
	docker-compose -f $(COMPOSE_FILE) build api

up:
	@echo "$(GREEN)🚀 Iniciando Marketing Cloud API...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Serviços iniciados!$(NC)"
	@echo "$(BLUE)📖 API: http://localhost:5000$(NC)"
	@echo "$(BLUE)🗄️  PgAdmin: http://localhost:8080$(NC)"
	@echo "$(BLUE)🔧 Redis Commander: http://localhost:8081$(NC)"

up-dev:
	@echo "$(GREEN)🚀 Iniciando em modo desenvolvimento...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up

up-prod:
	@echo "$(GREEN)🚀 Iniciando em modo produção...$(NC)"
	docker-compose -f $(COMPOSE_FILE) --profile production up -d

up-tools:
	@echo "$(GREEN)🚀 Iniciando com ferramentas...$(NC)"
	docker-compose -f $(COMPOSE_FILE) --profile tools up -d

down:
	@echo "$(RED)⏹️  Parando serviços...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down

down-volumes:
	@echo "$(RED)⏹️  Parando serviços e removendo volumes...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v

restart:
	@echo "$(YELLOW)🔄 Reiniciando serviços...$(NC)"
	docker-compose -f $(COMPOSE_FILE) restart

restart-api:
	@echo "$(YELLOW)🔄 Reiniciando API...$(NC)"
	docker-compose -f $(COMPOSE_FILE) restart api

logs:
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-api:
	docker-compose -f $(COMPOSE_FILE) logs -f api

logs-db:
	docker-compose -f $(COMPOSE_FILE) logs -f postgres

logs-redis:
	docker-compose -f $(COMPOSE_FILE) logs -f redis

status: #
	@echo "$(BLUE)📊 Status dos Serviços:$(NC)"
	docker-compose -f $(COMPOSE_FILE) ps
	@echo "\n$(BLUE)💾 Uso de Volumes:$(NC)"
	docker volume ls | grep $(PROJECT_NAME)
	@echo "\n$(BLUE)🌐 Redes:$(NC)"
	docker network ls | grep $(PROJECT_NAME)

health:
	@echo "$(BLUE)🏥 Verificando saúde dos serviços...$(NC)"
	@curl -s http://localhost:5000/health | jq '.' || echo "API não está respondendo"
	@docker-compose -f $(COMPOSE_FILE) exec postgres pg_isready || echo "PostgreSQL não está pronto"
	@docker-compose -f $(COMPOSE_FILE) exec redis redis-cli ping || echo "Redis não está respondendo"

populate:
	@echo "$(GREEN)📊 Populando banco de dados...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api python populate_data.py

populate-force:
	@echo "$(GREEN)📊 Populando banco de dados (limpeza forçada)...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api python -c "import os; os.environ['FORCE_POPULATE'] = 'true'; exec(open('populate_data.py').read())"

backup:
	@echo "$(YELLOW)💾 Fazendo backup do banco...$(NC)"
	@mkdir -p $(BACKUP_DIR)
	docker-compose -f $(COMPOSE_FILE) exec -T postgres pg_dump -U marketing_user marketing_cloud_db > $(BACKUP_DIR)/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup concluído!$(NC)"

restore:
	@echo "$(YELLOW)🔄 Restaurando backup...$(NC)"
	@if [ -z "$(BACKUP_FILE)" ]; then echo "$(RED)❌ Use: make restore BACKUP_FILE=arquivo.sql$(NC)"; exit 1; fi
	docker-compose -f $(COMPOSE_FILE) exec -T postgres psql -U marketing_user -d marketing_cloud_db < $(BACKUP_FILE)
	@echo "$(GREEN)✅ Restore concluído!$(NC)"

shell:
	docker-compose -f $(COMPOSE_FILE) exec api bash

shell-db:
	docker-compose -f $(COMPOSE_FILE) exec postgres psql -U marketing_user -d marketing_cloud_db

shell-redis:
	docker-compose -f $(COMPOSE_FILE) exec redis redis-cli

python-shell:
	docker-compose -f $(COMPOSE_FILE) exec api python -c "from app import *; import IPython; IPython.start_ipython(argv=[])"

test:
	@echo "$(BLUE)🧪 Executando testes...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api python -m pytest tests/ -v

test-coverage:
	@echo "$(BLUE)🧪 Executando testes com coverage...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api python -m pytest tests/ --cov=. --cov-report=html

lint:
	@echo "$(BLUE)🔍 Verificando qualidade do código...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api flake8 . --max-line-length=120
	docker-compose -f $(COMPOSE_FILE) exec api black --check .

format:
	@echo "$(BLUE)✨ Formatando código...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api black .
	docker-compose -f $(COMPOSE_FILE) exec api isort .

clean:
	@echo "$(RED)🧹 Limpando containers e imagens...$(NC)"
	docker system prune -f
	docker volume prune -f

clean-all:
	@echo "$(RED)🧹 Limpeza completa...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v --rmi all --remove-orphans
	docker system prune -a -f
	docker volume prune -f
	docker network prune -f

reset:
	@echo "$(RED)🔄 Reset completo do projeto...$(NC)"
	$(MAKE) down-volumes
	$(MAKE) clean-all
	$(MAKE) build
	$(MAKE) up
	$(MAKE) populate

deploy:
	@echo "$(GREEN)🚀 Deploy para produção...$(NC)"
	$(MAKE) build
	$(MAKE) up-prod
	@echo "$(GREEN)✅ Deploy concluído!$(NC)"

migrate:
	@echo "$(BLUE)🗄️  Executando migrações...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec api python -c "from app import db; db.create_all(); print('Migrações concluídas!')"

stats:
	@echo "$(BLUE)📈 Estatísticas de Recursos:$(NC)"
	docker stats --no-stream $(shell docker-compose -f $(COMPOSE_FILE) ps -q)

top:
	@echo "$(BLUE)⚡ Processos nos Containers:$(NC)"
	docker-compose -f $(COMPOSE_FILE) top

inspect:
	docker-compose -f $(COMPOSE_FILE) config

env-check:
	@echo "$(BLUE)🔧 Verificando variáveis de ambiente...$(NC)"
	@if [ -f .env ]; then echo "$(GREEN)✅ Arquivo .env encontrado$(NC)"; else echo "$(RED)❌ Arquivo .env não encontrado$(NC)"; fi
	@echo "$(BLUE)Principais variáveis:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec api python -c "import os; print('DATABASE_URL:', os.environ.get('DATABASE_URL', 'NÃO DEFINIDA')); print('REDIS_URL:', os.environ.get('REDIS_URL', 'NÃO DEFINIDA'))"

ports:
	@echo "$(BLUE)🌐 Portas dos Serviços:$(NC)"
	@echo "API: 5000"
	@echo "PostgreSQL: 5432"
	@echo "Redis: 6379"
	@echo "PgAdmin: 8080"
	@echo "Redis Commander: 8081"
	@echo "Nginx: 80, 443"

urls:
	@echo "$(BLUE)🔗 URLs dos Serviços:$(NC)"
	@echo "$(GREEN)API:$(NC) http://localhost:5000"
	@echo "$(GREEN)API Docs:$(NC) http://localhost:5000/v1"
	@echo "$(GREEN)Health Check:$(NC) http://localhost:5000/health"
	@echo "$(GREEN)PgAdmin:$(NC) http://localhost:8080"
	@echo "$(GREEN)Redis Commander:$(NC) http://localhost:8081"

demo:
	@echo "$(GREEN)🎭 Executando demonstração completa...$(NC)"
	$(MAKE) up
	sleep 30
	$(MAKE) populate
	@echo "$(GREEN)🎉 Demonstração pronta!$(NC)"
	@echo "$(BLUE)Acesse: http://localhost:5000/v1$(NC)"

quick-start:
	@echo "$(GREEN)⚡ Início rápido...$(NC)"
	$(MAKE) build
	$(MAKE) up
	sleep 30
	$(MAKE) populate
	$(MAKE) urls