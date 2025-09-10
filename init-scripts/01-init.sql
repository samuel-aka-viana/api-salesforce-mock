-- =============================================================================
-- MARKETING CLOUD API - INICIALIZAÇÃO POSTGRESQL
-- Script para configuração inicial do banco de dados
-- =============================================================================

-- Criar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Configurar timezone padrão
SET timezone = 'America/Sao_Paulo';

-- Criar usuário adicional para leitura (opcional)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'marketing_reader') THEN
        CREATE ROLE marketing_reader WITH LOGIN PASSWORD 'reader_password_2024';
    END IF;
END
$$;

-- Conceder permissões básicas ao usuário reader
GRANT CONNECT ON DATABASE marketing_cloud_db TO marketing_reader;
GRANT USAGE ON SCHEMA public TO marketing_reader;

-- Criar função para atualizar timestamp automaticamente
CREATE OR REPLACE FUNCTION update_modified_date()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_date = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Comentários informativos
COMMENT ON DATABASE marketing_cloud_db IS 'Banco de dados da Marketing Cloud API Clone';
COMMENT ON EXTENSION "uuid-ossp" IS 'Geração de UUIDs';
COMMENT ON EXTENSION "pg_trgm" IS 'Busca por similaridade de texto';
COMMENT ON EXTENSION "unaccent" IS 'Remoção de acentos para busca';

-- Configurações de performance
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Recarregar configurações
SELECT pg_reload_conf();

-- Log da inicialização
INSERT INTO pg_settings_log (name, setting, applied_at)
VALUES ('marketing_cloud_init', 'completed', CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Função para busca de texto com acentos
CREATE OR REPLACE FUNCTION search_text(text_column TEXT, search_term TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN unaccent(LOWER(text_column)) LIKE unaccent(LOWER('%' || search_term || '%'));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Função para gerar slugs
CREATE OR REPLACE FUNCTION generate_slug(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                unaccent(input_text),
                '[^a-zA-Z0-9\s]', '', 'g'
            ),
            '\s+', '-', 'g'
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Função para validar email
CREATE OR REPLACE FUNCTION is_valid_email(email TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Função para estatísticas de contatos
CREATE OR REPLACE FUNCTION get_contact_stats()
RETURNS TABLE(
    status TEXT,
    count BIGINT,
    percentage NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.status::TEXT,
        COUNT(*)::BIGINT,
        ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER()), 2) as percentage
    FROM contacts c
    GROUP BY c.status
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Função para relatório de campanhas
CREATE OR REPLACE FUNCTION get_campaign_performance(
    start_date DATE DEFAULT CURRENT_DATE - INTERVAL '30 days',
    end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE(
    campaign_id TEXT,
    campaign_name TEXT,
    total_sent INTEGER,
    total_opens INTEGER,
    total_clicks INTEGER,
    open_rate NUMERIC,
    click_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.campaign_id::TEXT,
        c.name::TEXT,
        c.total_sent,
        c.total_opens,
        c.total_clicks,
        CASE
            WHEN c.total_sent > 0 THEN ROUND((c.total_opens * 100.0 / c.total_sent), 2)
            ELSE 0
        END as open_rate,
        CASE
            WHEN c.total_sent > 0 THEN ROUND((c.total_clicks * 100.0 / c.total_sent), 2)
            ELSE 0
        END as click_rate
    FROM campaigns c
    WHERE c.created_date BETWEEN start_date AND end_date + INTERVAL '1 day'
    ORDER BY c.total_sent DESC;
END;
$$ LANGUAGE plpgsql;

-- Criar índices para performance (serão criados quando as tabelas existirem)
-- Estes comandos são executados de forma segura
DO $$
BEGIN
    -- Índices para tabela contacts (se existir)
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'contacts') THEN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contacts_email
        ON contacts(email_address);

        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contacts_status
        ON contacts(status);

        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contacts_created
        ON contacts(created_date);

        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contacts_modified
        ON contacts(modified_date);

        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contacts_name_search
        ON contacts USING gin(to_tsvector('portuguese', coalesce(first_name, '') || ' ' || coalesce(last_name, '')));
    END IF;

    -- Índices para tabela campaigns (se existir)
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'campaigns') THEN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaigns_status
        ON campaigns(status);

        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaigns_created
        ON campaigns(created_date);

        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaigns_start_date
        ON campaigns(start_date);
    END IF;

    -- Índices para tabela data_events (se existir)
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'data_events') THEN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_data_events_contact_key
        ON data_events(contact_key);

        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_data_events_type
        ON data_events(event_type);

        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_data_events_date
        ON data_events(event_date);

        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_data_events_campaign
        ON data_events(campaign_id);
    END IF;
END
$$;

-- Log de conclusão
DO $$
BEGIN
    RAISE NOTICE 'Marketing Cloud Database initialized successfully at %', CURRENT_TIMESTAMP;
END
$$;