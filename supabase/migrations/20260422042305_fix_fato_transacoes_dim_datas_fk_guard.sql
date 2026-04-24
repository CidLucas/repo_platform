BEGIN;

CREATE OR REPLACE FUNCTION analytics_v2.ensure_dim_data(p_data_id integer)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
	v_data_id integer;
	v_date date;
BEGIN
	IF p_data_id IS NULL OR p_data_id::text !~ '^\d{8}$' THEN
		v_data_id := to_char(current_date, 'YYYYMMDD')::integer;
	ELSE
		v_data_id := p_data_id;
	END IF;

	v_date := to_date(v_data_id::text, 'YYYYMMDD');

	INSERT INTO analytics_v2.dim_datas (
		data_id,
		data,
		ano,
		ano_iso,
		trimestre,
		nome_trimestre,
		mes,
		nome_mes,
		dia,
		dia_do_ano,
		semana_do_ano,
		dia_da_semana,
		nome_dia,
		e_fim_de_semana,
		primeiro_dia_mes,
		ultimo_dia_mes,
		e_inicio_mes,
		e_fim_mes,
		e_inicio_trimestre,
		e_fim_trimestre,
		e_inicio_ano,
		e_fim_ano
	)
	VALUES (
		v_data_id,
		v_date,
		EXTRACT(YEAR FROM v_date)::integer,
		EXTRACT(ISOYEAR FROM v_date)::integer,
		EXTRACT(QUARTER FROM v_date)::integer,
		'Q' || EXTRACT(QUARTER FROM v_date)::text,
		EXTRACT(MONTH FROM v_date)::integer,
		TO_CHAR(v_date, 'TMMonth'),
		EXTRACT(DAY FROM v_date)::integer,
		EXTRACT(DOY FROM v_date)::integer,
		EXTRACT(WEEK FROM v_date)::integer,
		EXTRACT(DOW FROM v_date)::integer,
		TO_CHAR(v_date, 'TMDay'),
		EXTRACT(DOW FROM v_date) IN (0, 6),
		date_trunc('month', v_date)::date,
		(date_trunc('month', v_date) + interval '1 month - 1 day')::date,
		v_date = date_trunc('month', v_date)::date,
		v_date = (date_trunc('month', v_date) + interval '1 month - 1 day')::date,
		v_date = date_trunc('quarter', v_date)::date,
		v_date = (date_trunc('quarter', v_date) + interval '3 month - 1 day')::date,
		v_date = date_trunc('year', v_date)::date,
		v_date = (date_trunc('year', v_date) + interval '1 year - 1 day')::date
	)
	ON CONFLICT (data_id) DO NOTHING;

	RETURN v_data_id;
END;
$$;

CREATE OR REPLACE FUNCTION analytics_v2.trg_ensure_dim_datas_for_fato()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
	NEW.data_competencia_id := analytics_v2.ensure_dim_data(NEW.data_competencia_id);

	IF NEW.data_efetiva_id IS NOT NULL THEN
		NEW.data_efetiva_id := analytics_v2.ensure_dim_data(NEW.data_efetiva_id);
	END IF;

	RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_ensure_dim_datas_for_fato ON analytics_v2.fato_transacoes;

CREATE TRIGGER trg_ensure_dim_datas_for_fato
BEFORE INSERT OR UPDATE OF data_competencia_id, data_efetiva_id
ON analytics_v2.fato_transacoes
FOR EACH ROW
EXECUTE FUNCTION analytics_v2.trg_ensure_dim_datas_for_fato();

-- Seed at least today's date key so current-date fallback always has a valid FK target.
SELECT analytics_v2.ensure_dim_data(to_char(current_date, 'YYYYMMDD')::integer);

-- Backfill any date keys already present in fato_transacoes (safe no-op when table is empty).
INSERT INTO analytics_v2.dim_datas (
	data_id,
	data,
	ano,
	ano_iso,
	trimestre,
	nome_trimestre,
	mes,
	nome_mes,
	dia,
	dia_do_ano,
	semana_do_ano,
	dia_da_semana,
	nome_dia,
	e_fim_de_semana,
	primeiro_dia_mes,
	ultimo_dia_mes,
	e_inicio_mes,
	e_fim_mes,
	e_inicio_trimestre,
	e_fim_trimestre,
	e_inicio_ano,
	e_fim_ano
)
SELECT
	d.data_id,
	v_date,
	EXTRACT(YEAR FROM v_date)::integer,
	EXTRACT(ISOYEAR FROM v_date)::integer,
	EXTRACT(QUARTER FROM v_date)::integer,
	'Q' || EXTRACT(QUARTER FROM v_date)::text,
	EXTRACT(MONTH FROM v_date)::integer,
	TO_CHAR(v_date, 'TMMonth'),
	EXTRACT(DAY FROM v_date)::integer,
	EXTRACT(DOY FROM v_date)::integer,
	EXTRACT(WEEK FROM v_date)::integer,
	EXTRACT(DOW FROM v_date)::integer,
	TO_CHAR(v_date, 'TMDay'),
	EXTRACT(DOW FROM v_date) IN (0, 6),
	date_trunc('month', v_date)::date,
	(date_trunc('month', v_date) + interval '1 month - 1 day')::date,
	v_date = date_trunc('month', v_date)::date,
	v_date = (date_trunc('month', v_date) + interval '1 month - 1 day')::date,
	v_date = date_trunc('quarter', v_date)::date,
	v_date = (date_trunc('quarter', v_date) + interval '3 month - 1 day')::date,
	v_date = date_trunc('year', v_date)::date,
	v_date = (date_trunc('year', v_date) + interval '1 year - 1 day')::date
FROM (
	SELECT DISTINCT data_competencia_id AS data_id
	FROM analytics_v2.fato_transacoes
	WHERE data_competencia_id IS NOT NULL AND data_competencia_id::text ~ '^\d{8}$'
) d
CROSS JOIN LATERAL to_date(d.data_id::text, 'YYYYMMDD') AS v_date
ON CONFLICT (data_id) DO NOTHING;

COMMIT;
