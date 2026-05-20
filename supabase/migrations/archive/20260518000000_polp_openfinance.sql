-- ── Polp Open Finance Integration ────────────────────────────────────────────
-- Tables to store bank connections and synced financial data from Polp API.
-- Blu holds one set of Polp API credentials (env vars); each client's bank
-- connections are stored here, referenced by polp_integration_id.

-- ── polp_integrations ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS polp_integrations (
  id                              uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id                       uuid        NOT NULL,
  polp_integration_id             integer     NOT NULL,
  institution_id                  integer     NOT NULL,
  status                          text        NOT NULL DEFAULT 'UPDATING',
  execution_status                text,
  error                           text,
  url_to_authenticate             text,
  url_to_authenticate_expires_at  timestamptz,
  last_updated_at                 timestamptz,
  next_auto_sync_at               timestamptz,
  created_at                      timestamptz NOT NULL DEFAULT now(),
  updated_at                      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, polp_integration_id)
);

CREATE INDEX IF NOT EXISTS polp_integrations_client_id_idx ON polp_integrations (client_id);

ALTER TABLE polp_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "client members read own polp integrations"
  ON polp_integrations FOR SELECT
  USING (
    client_id IN (
      SELECT client_id FROM client_users WHERE auth_user_id = auth.uid()
    )
  );

-- ── polp_accounts ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS polp_accounts (
  id                uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id         uuid        NOT NULL,
  integration_id    uuid        NOT NULL REFERENCES polp_integrations (id) ON DELETE CASCADE,
  polp_account_id   integer     NOT NULL,
  type              text        NOT NULL,        -- BANK | CREDIT
  subtype           text,                        -- CHECKING_ACCOUNT | SAVINGS_ACCOUNT | CREDIT_CARD …
  number            text,
  name              text,
  balance           numeric(15, 2) NOT NULL DEFAULT 0,
  currency_code     text        NOT NULL DEFAULT 'BRL',
  marketing_name    text,
  owner             text,
  bank_data         jsonb,
  credit_data       jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, polp_account_id)
);

CREATE INDEX IF NOT EXISTS polp_accounts_client_id_idx ON polp_accounts (client_id);
CREATE INDEX IF NOT EXISTS polp_accounts_integration_id_idx ON polp_accounts (integration_id);

ALTER TABLE polp_accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "client members read own polp accounts"
  ON polp_accounts FOR SELECT
  USING (
    client_id IN (
      SELECT client_id FROM client_users WHERE auth_user_id = auth.uid()
    )
  );

-- ── polp_transactions ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS polp_transactions (
  id                   uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id            uuid        NOT NULL,
  polp_account_id      integer     NOT NULL,
  polp_transaction_id  integer     NOT NULL,
  external_id          text,
  description          text,
  amount               numeric(15, 2) NOT NULL,
  currency_code        text        NOT NULL DEFAULT 'BRL',
  date                 date        NOT NULL,
  type                 text        NOT NULL,     -- DEBIT | CREDIT
  status               text,                    -- POSTED | PENDING
  balance_after        numeric(15, 2),
  category             jsonb,
  merchant             jsonb,
  payment_data         jsonb,
  credit_card_metadata jsonb,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, polp_transaction_id)
);

CREATE INDEX IF NOT EXISTS polp_transactions_client_id_date_idx ON polp_transactions (client_id, date DESC);
CREATE INDEX IF NOT EXISTS polp_transactions_polp_account_id_idx ON polp_transactions (polp_account_id);

ALTER TABLE polp_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "client members read own polp transactions"
  ON polp_transactions FOR SELECT
  USING (
    client_id IN (
      SELECT client_id FROM client_users WHERE auth_user_id = auth.uid()
    )
  );

-- ── polp_bills ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS polp_bills (
  id                      uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id               uuid        NOT NULL,
  polp_account_id         integer     NOT NULL,
  polp_bill_id            integer     NOT NULL,
  due_date                date        NOT NULL,
  total_amount            numeric(15, 2) NOT NULL,
  minimum_payment_amount  numeric(15, 2),
  currency_code           text        NOT NULL DEFAULT 'BRL',
  allows_installments     boolean,
  finance_charges         jsonb,
  payments                jsonb,
  status                  text        NOT NULL DEFAULT 'open',  -- open | paid | overdue
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, polp_bill_id)
);

CREATE INDEX IF NOT EXISTS polp_bills_client_id_due_date_idx ON polp_bills (client_id, due_date ASC);

ALTER TABLE polp_bills ENABLE ROW LEVEL SECURITY;

CREATE POLICY "client members read own polp bills"
  ON polp_bills FOR SELECT
  USING (
    client_id IN (
      SELECT client_id FROM client_users WHERE auth_user_id = auth.uid()
    )
  );

-- ── updated_at triggers ───────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION polp_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER polp_integrations_updated_at
  BEFORE UPDATE ON polp_integrations
  FOR EACH ROW EXECUTE FUNCTION polp_set_updated_at();

CREATE TRIGGER polp_accounts_updated_at
  BEFORE UPDATE ON polp_accounts
  FOR EACH ROW EXECUTE FUNCTION polp_set_updated_at();

CREATE TRIGGER polp_transactions_updated_at
  BEFORE UPDATE ON polp_transactions
  FOR EACH ROW EXECUTE FUNCTION polp_set_updated_at();

CREATE TRIGGER polp_bills_updated_at
  BEFORE UPDATE ON polp_bills
  FOR EACH ROW EXECUTE FUNCTION polp_set_updated_at();
