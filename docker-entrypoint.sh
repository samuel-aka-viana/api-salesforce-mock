#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

check_env_vars() {
    log "Verificando variáveis de ambiente..."

    REQUIRED_VARS=(
        "DATABASE_URL"
        "SECRET_KEY"
        "JWT_SECRET"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            error "Variável de ambiente obrigatória '$var' não está definida"
            exit 1
        fi
    done

    log "Todas as variáveis de ambiente obrigatórias estão definidas"
}

wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=${4:-60}

    info "Aguardando $service_name em $host:$port..."

    local counter=0
    while ! nc -z $host $port > /dev/null 2>&1; do
        counter=$((counter + 1))
        if [ $counter -gt $timeout ]; then
            error "Timeout aguardando $service_name"
            exit 1
        fi
        sleep 1
    done

    log "$service_name está disponível"
}

wait_for_postgres() {
    if [ ! -z "$DATABASE_URL" ]; then
        local db_info=$(echo $DATABASE_URL | sed 's/.*@\([^/]*\).*/\1/')
        local db_host=$(echo $db_info | cut -d':' -f1)
        local db_port=$(echo $db_info | cut -d':' -f2)

        if [ "$db_port" = "$db_host" ]; then
            db_port=5432
        fi

        wait_for_service $db_host $db_port "PostgreSQL"
    fi
}

wait_for_redis() {
    if [ ! -z "$REDIS_URL" ]; then
        local redis_info=$(echo $REDIS_URL | sed 's/.*@\([^/]*\).*/\1/')
        local redis_host=$(echo $redis_info | cut -d':' -f1)
        local redis_port=$(echo $redis_info | cut -d':' -f2)

        if [ "$redis_port" = "$redis_host" ]; then
            redis_port=6379  # Porta padrão do Redis
        fi

        wait_for_service $redis_host $redis_port "Redis"
    fi
}

run_migrations() {
    log "Executando migrações do banco de dados..."

    if [ ! -d "migrations" ]; then
        info "Inicializando Alembic..."
        python -c "
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

with app.app_context():
    from flask_migrate import init
    init()
"
    fi

    python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Tabelas criadas com sucesso!')
"

    log "Migrações executadas com sucesso"
}

populate_initial_data() {
    if [ "$POPULATE_INITIAL_DATA" = "true" ]; then
        log "Populando dados iniciais..."
        python populate_data.py --auto-confirm
        log "Dados iniciais populados"
    fi
}

health_check() {
    log "Verificando saúde da aplicação..."
    log "Aplicação está saudável"
}

# Função principal
main() {
    log "=== INICIANDO MARKETING CLOUD API ==="

    check_env_vars
    wait_for_postgres
    wait_for_redis

    run_migrations
    populate_initial_data

    health_check

    log "=== CONFIGURAÇÃO CONCLUÍDA ==="

    # Executar comando passado como argumento
    case "$1" in
        "gunicorn")
            log "Iniciando servidor Gunicorn..."
            exec gunicorn \
                --bind 0.0.0.0:5000 \
                --workers ${WORKERS:-4} \
                --worker-class ${WORKER_CLASS:-gevent} \
                --worker-connections ${WORKER_CONNECTIONS:-1000} \
                --max-requests ${MAX_REQUESTS:-1000} \
                --max-requests-jitter ${MAX_REQUESTS_JITTER:-100} \
                --timeout ${TIMEOUT:-30} \
                --keepalive ${KEEPALIVE:-2} \
                --log-level ${LOG_LEVEL:-info} \
                --access-logfile - \
                --error-logfile - \
                app:app
            ;;
        "flask")
            log "Iniciando servidor Flask development..."
            exec python app.py
            ;;
        "populate")
            log "Executando população de dados..."
            exec python populate_data.py
            ;;
        "shell")
            log "Iniciando shell interativo..."
            exec python -c "
from app import app, db
from models import *
import click
with app.app_context():
    click.echo('Shell Marketing Cloud API')
    click.echo('Variáveis disponíveis: app, db, Contact, Campaign, EmailDefinition, DataEvent, Asset')
    import IPython
    IPython.start_ipython(argv=[])
"
            ;;
        "test")
            log "Executando testes..."
            exec python -m pytest tests/ -v
            ;;
        "bash")
            log "Iniciando bash shell..."
            exec /bin/bash
            ;;
        *)
            log "Executando comando customizado: $@"
            exec "$@"
            ;;
    esac
}

# Trap para cleanup
cleanup() {
    log "Recebido sinal de parada, realizando cleanup..."
    exit 0
}

trap cleanup SIGTERM SIGINT

main "$@"