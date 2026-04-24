BEGIN;

CREATE OR REPLACE FUNCTION public.create_bigquery_server(
	p_client_id uuid,
	p_service_account_key jsonb,
	p_project_id text,
	p_dataset_id text,
	p_location text DEFAULT 'US'
) RETURNS jsonb AS $$
DECLARE
	v_server_name text;
	v_vault_key_id uuid;
	v_key_name text;
	v_existing_vault_key_id uuid;
	v_existing_secret_id uuid;
BEGIN
	IF p_client_id IS NULL OR p_service_account_key IS NULL THEN
		RAISE EXCEPTION 'client_id and service_account_key are required';
	END IF;

	v_server_name := 'bigquery_' || p_client_id;
	v_key_name := v_server_name || '_sa_key';

	IF EXISTS (SELECT 1 FROM public.bigquery_servers WHERE client_id = p_client_id) THEN
		SELECT vault_key_id INTO v_existing_vault_key_id
		FROM public.bigquery_servers
		WHERE client_id = p_client_id;

		EXECUTE format('drop server if exists %I cascade', v_server_name);

		IF v_existing_vault_key_id IS NOT NULL THEN
			DELETE FROM vault.secrets
			WHERE id = v_existing_vault_key_id;
		END IF;

		DELETE FROM public.bigquery_servers
		WHERE client_id = p_client_id;
	END IF;

	SELECT id INTO v_existing_secret_id
	FROM vault.secrets
	WHERE name = v_key_name
	LIMIT 1;

	IF v_existing_secret_id IS NOT NULL THEN
		DELETE FROM vault.secrets
		WHERE id = v_existing_secret_id;
	END IF;

	SELECT vault.create_secret(
		p_service_account_key::text,
		v_key_name,
		'BigQuery service account for client ' || p_client_id
	) INTO v_vault_key_id;

	EXECUTE format(
		'create server if not exists %I
		 foreign data wrapper bigquery_wrapper
		 options (
			 sa_key_id %L,
			 project_id %L,
			 dataset_id %L,
			 location %L
		 )',
		v_server_name,
		v_vault_key_id::text,
		p_project_id,
		p_dataset_id,
		p_location
	);

	INSERT INTO public.bigquery_servers (
		client_id,
		server_name,
		project_id,
		dataset_id,
		vault_key_id,
		location
	) VALUES (
		p_client_id,
		v_server_name,
		p_project_id,
		p_dataset_id,
		v_vault_key_id,
		p_location
	);

	RETURN jsonb_build_object(
		'success', true,
		'server_name', v_server_name,
		'client_id', p_client_id,
		'project_id', p_project_id,
		'dataset_id', p_dataset_id,
		'vault_key_id', v_vault_key_id
	);
EXCEPTION
	WHEN OTHERS THEN
		RETURN jsonb_build_object(
			'success', false,
			'error', SQLERRM
		);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.create_bigquery_server(uuid, jsonb, text, text, text)
IS 'Creates or replaces a BigQuery foreign server for a client and stores the service account in Vault';

GRANT EXECUTE ON FUNCTION public.create_bigquery_server(uuid, jsonb, text, text, text)
TO authenticated, service_role;

COMMIT;
