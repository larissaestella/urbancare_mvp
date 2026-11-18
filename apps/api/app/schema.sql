-- Sem coluna de imagem nem identificador de pessoa: só contagem anônima por ponto.
CREATE TABLE IF NOT EXISTS lines (
    id          text PRIMARY KEY,
    headway_min integer NOT NULL
);
CREATE TABLE IF NOT EXISTS garages (
    id   text PRIMARY KEY,
    name text NOT NULL
);
CREATE TABLE IF NOT EXISTS stops (
    id           text PRIMARY KEY,
    name         text NOT NULL,
    svg_x        real,
    svg_y        real,
    arrival_rate real NOT NULL,   -- pessoas/min no horário de referência
    board_rate   real NOT NULL,   -- pessoas/min embarcando
    steady       boolean NOT NULL DEFAULT false  -- Demo: lotação fixa até o despacho chegar
);
CREATE TABLE IF NOT EXISTS stop_lines (
    stop_id text REFERENCES stops(id),
    line_id text REFERENCES lines(id),
    PRIMARY KEY (stop_id, line_id)
);
CREATE TABLE IF NOT EXISTS readings (
    stop_id text NOT NULL,
    ts      timestamptz NOT NULL,
    count   integer NOT NULL CHECK (count >= 0),
    PRIMARY KEY (stop_id, ts)
);
-- TimescaleDB quando disponível (Docker local, Render Postgres); sem ele, readings fica uma tabela comum.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb;
    PERFORM create_hypertable('readings', 'ts', if_not_exists => true);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'TimescaleDB indisponível: readings sem hypertable (%)', SQLERRM;
END $$;
CREATE TABLE IF NOT EXISTS stop_state (
    stop_id      text PRIMARY KEY REFERENCES stops(id),
    count        integer NOT NULL,
    last_ts      timestamptz,
    over_since   timestamptz,
    alert_active boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS alerts (
    id         serial PRIMARY KEY,
    stop_id    text NOT NULL REFERENCES stops(id),
    over_since timestamptz NOT NULL,
    opened_at  timestamptz NOT NULL,
    closed_at  timestamptz,
    peak       integer NOT NULL
);
CREATE TABLE IF NOT EXISTS dispatches (
    id         serial PRIMARY KEY,
    stop_id    text NOT NULL REFERENCES stops(id),
    garage_id  text NOT NULL REFERENCES garages(id),
    created_at timestamptz NOT NULL,
    arrive_at  timestamptz NOT NULL,
    status     text NOT NULL,
    boards     integer NOT NULL
);
CREATE TABLE IF NOT EXISTS hourly_network (
    hour   smallint PRIMARY KEY,   -- 5..22
    avg_4w integer NOT NULL,       -- média das 4 semanas (também é a previsão)
    today  integer                 -- horas já fechadas do dia do cenário
);
-- Landing do smoke test (relógio de parede, não de sim). Só os 3 campos do formulário, a variante e um id
-- aleatório do navegador: sem IP, sem user agent. Visita e clique contam uma vez por visitante e variante.
CREATE TABLE IF NOT EXISTS events (
    visitor text NOT NULL,
    variant char(1) NOT NULL CHECK (variant IN ('A', 'B')),
    kind    text NOT NULL CHECK (kind IN ('visit', 'click')),
    ts      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (visitor, variant, kind)
);
CREATE TABLE IF NOT EXISTS leads (
    id         serial PRIMARY KEY,
    visitor    text NOT NULL,
    variant    char(1) NOT NULL CHECK (variant IN ('A', 'B')),
    company    text NOT NULL,
    size       integer NOT NULL CHECK (size > 0),   -- quantidade estimada de linhas/pontos
    email      text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (visitor, variant)
);
-- Cadastro cidadão (Extração Automática de Endereços): só endereços confirmados pelo próprio usuário, com
-- consentimento. Nenhuma imagem, nome ou documento é guardado; o id do titular é aleatório do navegador e cada
-- endereço pode ser excluído por ele. Endereço repetido do mesmo titular atualiza a data em vez de duplicar.
CREATE TABLE IF NOT EXISTS citizen_addresses (
    id           serial PRIMARY KEY,
    visitor      text NOT NULL,
    issuer       text NOT NULL CHECK (issuer IN ('ENEL', 'VIVO', 'CLARO')),
    street       text NOT NULL,
    number       text NOT NULL,
    complement   text NOT NULL DEFAULT '',
    neighborhood text NOT NULL,
    city         text NOT NULL,
    state        char(2) NOT NULL,
    postal_code  char(9) NOT NULL,
    confirmed_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (visitor, street, number, complement, postal_code)
);
