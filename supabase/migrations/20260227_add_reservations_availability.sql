-- Migration: Add reservation and availability tables for resource tracking
-- This migration implements the Option B schema described by the user.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist";   -- for exclusion constraints

-- Dimension tables

-- dim_inventory (enhanced version of dim_produtos)
CREATE TABLE IF NOT EXISTS analytics_v2.dim_inventory (
    inventory_id        UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id           TEXT NOT NULL,
    sku                 TEXT,
    nome                TEXT NOT NULL,
    inventory_type      TEXT NOT NULL CHECK (inventory_type IN ('consumable', 'asset')),
    tracking_method     TEXT DEFAULT 'quantity' CHECK (tracking_method IN ('quantity', 'serialized', 'lot')),
    category_id         UUID REFERENCES analytics_v2.dim_categoria(categoria_id),
    quantidade_total_vendida NUMERIC DEFAULT 0,
    receita_total            NUMERIC DEFAULT 0,
    preco_medio              NUMERIC DEFAULT 0,
    total_pedidos            INTEGER DEFAULT 0,
    current_stock        NUMERIC DEFAULT 0,
    minimum_stock        NUMERIC,
    location             TEXT,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE analytics_v2.dim_inventory ENABLE ROW LEVEL SECURITY;
CREATE POLICY dim_inventory_policy ON analytics_v2.dim_inventory
    USING (client_id = current_setting('app.current_client_id')::TEXT);

-- dim_resources
CREATE TABLE IF NOT EXISTS analytics_v2.dim_resources (
    resource_id     UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id       TEXT NOT NULL,
    name            TEXT NOT NULL,
    resource_type   TEXT NOT NULL CHECK (resource_type IN ('room', 'table', 'equipment', 'vehicle', 'other')),
    capacity        INT,
    attributes      JSONB,
    status          TEXT DEFAULT 'active' CHECK (status IN ('active','maintenance','retired')),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE analytics_v2.dim_resources ENABLE ROW LEVEL SECURITY;
CREATE POLICY dim_resources_policy ON analytics_v2.dim_resources
    USING (client_id = current_setting('app.current_client_id')::TEXT);


-- Fact tables

-- fato_transacoes modifications are assumed already present in earlier migrations; ensure columns exist
ALTER TABLE analytics_v2.fato_transacoes
    ADD COLUMN IF NOT EXISTS inventory_id UUID REFERENCES analytics_v2.dim_inventory(inventory_id),
    ADD COLUMN IF NOT EXISTS movement_type TEXT CHECK (movement_type IN ('purchase','sale','return','adjustment','transfer')),
    ADD COLUMN IF NOT EXISTS origem_tabela TEXT,
    ADD COLUMN IF NOT EXISTS origem_id UUID,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- indexes (if not already present)
CREATE INDEX IF NOT EXISTS idx_fato_transacoes_client_id ON analytics_v2.fato_transacoes(client_id);
CREATE INDEX IF NOT EXISTS idx_fato_transacoes_inventory_id ON analytics_v2.fato_transacoes(inventory_id);
CREATE INDEX IF NOT EXISTS idx_fato_transacoes_data_efetiva_id ON analytics_v2.fato_transacoes(data_efetiva_id);

-- fact_reservations
CREATE TABLE IF NOT EXISTS analytics_v2.fact_reservations (
    reservation_id      UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id           TEXT NOT NULL,
    resource_id         UUID REFERENCES analytics_v2.dim_resources(resource_id) NOT NULL,
    customer_id         UUID REFERENCES analytics_v2.dim_clientes(cliente_id) NOT NULL,
    booking_date_id     INTEGER REFERENCES analytics_v2.dim_datas(data_id) NOT NULL,
    check_in_date_id    INTEGER REFERENCES analytics_v2.dim_datas(data_id) NOT NULL,
    check_out_date_id   INTEGER REFERENCES analytics_v2.dim_datas(data_id) NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('provisional', 'confirmed', 'checked_in', 'checked_out', 'cancelled', 'no_show')),
    number_of_guests    INT,
    total_amount        NUMERIC,
    paid_amount         NUMERIC DEFAULT 0,
    currency            TEXT DEFAULT 'BRL',
    source              TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE analytics_v2.fact_reservations ENABLE ROW LEVEL SECURITY;
CREATE POLICY fact_reservations_policy ON analytics_v2.fact_reservations
    USING (client_id = current_setting('app.current_client_id')::TEXT);

CREATE INDEX IF NOT EXISTS idx_fact_reservations_client_id ON analytics_v2.fact_reservations(client_id);
CREATE INDEX IF NOT EXISTS idx_fact_reservations_resource_id ON analytics_v2.fact_reservations(resource_id);
CREATE INDEX IF NOT EXISTS idx_fact_reservations_dates ON analytics_v2.fact_reservations(check_in_date_id, check_out_date_id);

-- fact_availability
CREATE TABLE IF NOT EXISTS analytics_v2.fact_availability (
    availability_id   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id         TEXT NOT NULL,
    resource_id       UUID REFERENCES analytics_v2.dim_resources(resource_id) NOT NULL,
    start_date        DATE NOT NULL,
    end_date          DATE NOT NULL,
    reason            TEXT NOT NULL CHECK (reason IN ('reservation', 'maintenance', 'blocked')),
    reservation_id    UUID REFERENCES analytics_v2.fact_reservations(reservation_id) ON DELETE CASCADE,
    description       TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- exclusion constraint to prevent overlaps
ALTER TABLE analytics_v2.fact_availability
    DROP CONSTRAINT IF EXISTS no_overlap_per_resource;
ALTER TABLE analytics_v2.fact_availability
    ADD CONSTRAINT no_overlap_per_resource
    EXCLUDE USING gist (resource_id WITH =, daterange(start_date, end_date, '[)') WITH &&);

ALTER TABLE analytics_v2.fact_availability ENABLE ROW LEVEL SECURITY;
CREATE POLICY fact_availability_policy ON analytics_v2.fact_availability
    USING (client_id = current_setting('app.current_client_id')::TEXT);

CREATE INDEX IF NOT EXISTS idx_fact_availability_client_id ON analytics_v2.fact_availability(client_id);
CREATE INDEX IF NOT EXISTS idx_fact_availability_resource_id ON analytics_v2.fact_availability(resource_id);
CREATE INDEX IF NOT EXISTS idx_fact_availability_dates ON analytics_v2.fact_availability(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_fact_availability_reservation_id ON analytics_v2.fact_availability(reservation_id) WHERE reservation_id IS NOT NULL;

-- triggers to keep availability in sync with reservations

CREATE OR REPLACE FUNCTION analytics_v2.sync_reservation_availability()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.status = 'confirmed' THEN
            INSERT INTO analytics_v2.fact_availability(
                client_id, resource_id, start_date, end_date, reason, reservation_id
            )
            SELECT NEW.client_id, NEW.resource_id,
                   d1.data, d2.data, 'reservation', NEW.reservation_id
            FROM analytics_v2.dim_datas d1, analytics_v2.dim_datas d2
            WHERE d1.data_id = NEW.check_in_date_id AND d2.data_id = NEW.check_out_date_id;
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        -- if reservation became confirmed
        IF NEW.status = 'confirmed' AND OLD.status <> 'confirmed' THEN
            INSERT INTO analytics_v2.fact_availability(
                client_id, resource_id, start_date, end_date, reason, reservation_id
            )
            SELECT NEW.client_id, NEW.resource_id,
                   d1.data, d2.data, 'reservation', NEW.reservation_id
            FROM analytics_v2.dim_datas d1, analytics_v2.dim_datas d2
            WHERE d1.data_id = NEW.check_in_date_id AND d2.data_id = NEW.check_out_date_id;
        ELSIF OLD.status = 'confirmed' AND NEW.status IN ('cancelled','no_show') THEN
            DELETE FROM analytics_v2.fact_availability WHERE reservation_id = OLD.reservation_id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        DELETE FROM analytics_v2.fact_availability WHERE reservation_id = OLD.reservation_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_fact_reservations_sync_availability ON analytics_v2.fact_reservations;
CREATE TRIGGER trg_fact_reservations_sync_availability
AFTER INSERT OR UPDATE OR DELETE ON analytics_v2.fact_reservations
FOR EACH ROW EXECUTE FUNCTION analytics_v2.sync_reservation_availability();
