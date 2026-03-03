-- Add RPC function to trigger column discovery from a credential_id
-- This function gets the credential details and triggers auto-discovery

CREATE OR REPLACE FUNCTION public.trigger_column_discovery(
  p_credential_id BIGINT
) RETURNS JSONB AS $$
DECLARE
  v_client_id TEXT;
  v_dataset_id TEXT;
  v_table_name TEXT;
  v_project_id TEXT;
  v_columns JSONB;
  v_column_count INTEGER;
  v_data_source_id UUID;
  v_foreign_table_name TEXT;
BEGIN
  RAISE LOG '[trigger_discovery] Starting discovery for credential_id=%', p_credential_id;

  -- Get credential details
  SELECT
    c.client_id,
    c.connection_metadata->>'dataset_id' AS dataset_id,
    c.connection_metadata->>'table_name' AS table_name,
    c.connection_metadata->>'project_id' AS project_id
  INTO v_client_id, v_dataset_id, v_table_name, v_project_id
  FROM credencial_servico_externo c
  WHERE c.id = p_credential_id;

  IF v_client_id IS NULL THEN
    RAISE LOG '[trigger_discovery] ERROR: Credential % not found', p_credential_id;
    RETURN jsonb_build_object(
      'success', FALSE,
      'error', 'Credential not found'
    );
  END IF;

  RAISE LOG '[trigger_discovery] Got credential: client_id=%, dataset=%, table=%, project=%',
    v_client_id, v_dataset_id, v_table_name, v_project_id;

  -- Build the foreign table name (schema.table)
  v_foreign_table_name := v_dataset_id || '.' || v_table_name;

  -- Query information_schema to get column metadata
  SELECT jsonb_agg(
    jsonb_build_object(
      'name', column_name,
      'type', data_type,
      'position', ordinal_position,
      'is_nullable', is_nullable = 'YES',
      'character_maximum_length', character_maximum_length,
      'numeric_precision', numeric_precision,
      'numeric_scale', numeric_scale
    ) ORDER BY ordinal_position
  )
  INTO v_columns
  FROM information_schema.columns
  WHERE table_schema || '.' || table_name = v_foreign_table_name
    AND table_catalog = current_catalog;

  IF v_columns IS NULL THEN
    RAISE LOG '[trigger_discovery] ERROR: No columns found for foreign table: %', v_foreign_table_name;
    RETURN jsonb_build_object(
      'success', FALSE,
      'error', 'Foreign table not found or has no columns: ' || v_foreign_table_name,
      'foreign_table_name', v_foreign_table_name
    );
  END IF;

  v_column_count := jsonb_array_length(v_columns);
  RAISE LOG '[trigger_discovery] Discovered % columns from foreign table %',
    v_column_count, v_foreign_table_name;

  -- Check if data source record exists for this credential
  SELECT id INTO v_data_source_id
  FROM public.client_data_sources
  WHERE credential_id = p_credential_id
  LIMIT 1;

  IF v_data_source_id IS NOT NULL THEN
    -- Update existing record
    UPDATE public.client_data_sources
    SET
      source_columns = v_columns,
      sync_status = 'ready',
      atualizado_em = NOW()
    WHERE id = v_data_source_id;

    RAISE LOG '[trigger_discovery] Updated existing data source id=%', v_data_source_id;
  ELSE
    -- Create new record
    INSERT INTO public.client_data_sources (
      client_id,
      credential_id,
      source_type,
      resource_type,
      storage_type,
      storage_location,
      source_columns,
      sync_status
    ) VALUES (
      v_client_id,
      p_credential_id,
      'bigquery',
      'invoices', -- Default, can be updated later
      'foreign_table',
      v_foreign_table_name,
      v_columns,
      'ready'
    )
    RETURNING id INTO v_data_source_id;

    RAISE LOG '[trigger_discovery] Created new data source record with id=%', v_data_source_id;
  END IF;

  RETURN jsonb_build_object(
    'success', TRUE,
    'column_count', v_column_count,
    'data_source_id', v_data_source_id,
    'columns', v_columns,
    'foreign_table_name', v_foreign_table_name
  );

EXCEPTION
  WHEN OTHERS THEN
    RAISE LOG '[trigger_discovery] ERROR: % - %', SQLERRM, SQLSTATE;
    RETURN jsonb_build_object(
      'success', FALSE,
      'error', SQLERRM,
      'error_code', SQLSTATE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.trigger_column_discovery(BIGINT) IS
  'Triggers automatic column discovery for a credential, populating client_data_sources';

-- Grant access to authenticated users
GRANT EXECUTE ON FUNCTION public.trigger_column_discovery(BIGINT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.trigger_column_discovery(BIGINT) TO service_role;
