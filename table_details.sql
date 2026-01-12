| table_name                 | column_name             | data_type                | is_nullable | column_comment |
| -------------------------- | ----------------------- | ------------------------ | ----------- | -------------- |
| client_data_sources        | id                      | uuid                     | NO          | null           |
| client_data_sources        | client_id               | text                     | NO          | null           |
| client_data_sources        | source_type             | text                     | NO          | null           |
| client_data_sources        | resource_type           | text                     | NO          | null           |
| client_data_sources        | storage_type            | text                     | NO          | null           |
| client_data_sources        | storage_location        | text                     | NO          | null           |
| client_data_sources        | column_mapping          | jsonb                    | YES         | null           |
| client_data_sources        | last_synced_at          | timestamp with time zone | YES         | null           |
| client_data_sources        | sync_status             | text                     | YES         | null           |
| client_data_sources        | error_message           | text                     | YES         | null           |
| client_data_sources        | created_at              | timestamp with time zone | YES         | null           |
| client_data_sources        | updated_at              | timestamp with time zone | YES         | null           |
| connector_sync_history     | id                      | uuid                     | NO          | null           |
| connector_sync_history     | credential_id           | integer                  | NO          | null           |
| connector_sync_history     | status                  | text                     | NO          | null           |
| connector_sync_history     | sync_started_at         | timestamp with time zone | NO          | null           |
| connector_sync_history     | sync_completed_at       | timestamp with time zone | YES         | null           |
| connector_sync_history     | duration_seconds        | integer                  | YES         | null           |
| connector_sync_history     | records_processed       | integer                  | YES         | null           |
| connector_sync_history     | records_inserted        | integer                  | YES         | null           |
| connector_sync_history     | records_updated         | integer                  | YES         | null           |
| connector_sync_history     | records_failed          | integer                  | YES         | null           |
| connector_sync_history     | resource_type           | text                     | YES         | null           |
| connector_sync_history     | error_message           | text                     | YES         | null           |
| connector_sync_history     | created_at              | timestamp with time zone | NO          | null           |
| connector_sync_history     | updated_at              | timestamp with time zone | NO          | null           |
| credencial_servico_externo | nome_servico            | character varying        | NO          | null           |
| credencial_servico_externo | id                      | integer                  | NO          | null           |
| credencial_servico_externo | client_id         | uuid                     | NO          | null           |
| credencial_servico_externo | tipo_servico            | text                     | YES         | null           |
| credencial_servico_externo | status                  | text                     | YES         | null           |
| credencial_servico_externo | credenciais_cifradas    | text                     | YES         | null           |
| credencial_servico_externo | created_at              | timestamp with time zone | YES         | null           |
| credencial_servico_externo | updated_at              | timestamp with time zone | YES         | null           |
| data_source_credentials    | id                      | uuid                     | NO          | null           |
| data_source_credentials    | client_id         | character varying        | NO          | null           |
| data_source_credentials    | nome_conexao            | character varying        | NO          | null           |
| data_source_credentials    | tipo_servico            | character varying        | NO          | null           |
| data_source_credentials    | secret_manager_id       | character varying        | YES         | null           |
| data_source_credentials    | status                  | character varying        | YES         | null           |
| data_source_credentials    | connection_metadata     | jsonb                    | YES         | null           |
| data_source_credentials    | last_sync_at            | timestamp with time zone | YES         | null           |
| data_source_credentials    | created_at              | timestamp with time zone | YES         | null           |
| data_source_credentials    | updated_at              | timestamp with time zone | YES         | null           |
| data_source_mappings       | id                      | uuid                     | NO          | null           |
| data_source_mappings       | credential_id           | uuid                     | NO          | null           |
| data_source_mappings       | client_id         | character varying        | NO          | null           |
| data_source_mappings       | source_type             | character varying        | NO          | null           |
| data_source_mappings       | source_resource         | character varying        | NO          | null           |
| data_source_mappings       | source_table_full_name  | character varying        | YES         | null           |
| data_source_mappings       | source_columns          | jsonb                    | NO          | null           |
| data_source_mappings       | source_sample_data      | jsonb                    | YES         | null           |
| data_source_mappings       | column_mapping          | jsonb                    | NO          | null           |
| data_source_mappings       | unmapped_columns        | jsonb                    | YES         | null           |
| data_source_mappings       | ignored_columns         | jsonb                    | YES         | null           |
| data_source_mappings       | match_confidence        | jsonb                    | YES         | null           |
| data_source_mappings       | status                  | character varying        | YES         | null           |
| data_source_mappings       | is_auto_generated       | boolean                  | YES         | null           |
| data_source_mappings       | reviewed_by             | character varying        | YES         | null           |
| data_source_mappings       | reviewed_at             | timestamp with time zone | YES         | null           |
| data_source_mappings       | created_at              | timestamp with time zone | YES         | null           |
| data_source_mappings       | updated_at              | timestamp with time zone | YES         | null           |
| ingestion_jobs             | id                      | uuid                     | NO          | null           |
| ingestion_jobs             | credential_id           | uuid                     | NO          | null           |
| ingestion_jobs             | mapping_id              | uuid                     | YES         | null           |
| ingestion_jobs             | client_id         | character varying        | NO          | null           |
| ingestion_jobs             | job_id                  | character varying        | NO          | null           |
| ingestion_jobs             | pubsub_message_id       | character varying        | YES         | null           |
| ingestion_jobs             | source_resource         | character varying        | NO          | null           |
| ingestion_jobs             | target_table            | character varying        | YES         | null           |
| ingestion_jobs             | status                  | character varying        | YES         | null           |
| ingestion_jobs             | progress_percent        | integer                  | YES         | null           |
| ingestion_jobs             | records_extracted       | integer                  | YES         | null           |
| ingestion_jobs             | records_loaded          | integer                  | YES         | null           |
| ingestion_jobs             | error_message           | text                     | YES         | null           |
| ingestion_jobs             | error_details           | jsonb                    | YES         | null           |
| ingestion_jobs             | started_at              | timestamp with time zone | YES         | null           |
| ingestion_jobs             | completed_at            | timestamp with time zone | YES         | null           |
| ingestion_jobs             | created_at              | timestamp with time zone | YES         | null           |
| ingestion_jobs             | updated_at              | timestamp with time zone | YES         | null           |
| integration_configs        | id                      | uuid                     | NO          | null           |
| integration_configs        | client_id         | uuid                     | NO          | null           |
| integration_configs        | provider                | text                     | YES         | null           |
| integration_configs        | config_type             | text                     | YES         | null           |
| integration_configs        | client_id_encrypted     | text                     | YES         | null           |
| integration_configs        | client_secret_encrypted | text                     | YES         | null           |
| integration_configs        | redirect_uri            | text                     | YES         | null           |
| integration_configs        | scopes                  | jsonb                    | YES         | null           |
| integration_configs        | created_at              | timestamp with time zone | YES         | null           |
| integration_configs        | updated_at              | timestamp with time zone | YES         | null           |
| integration_tokens         | id                      | uuid                     | NO          | null           |
| integration_tokens         | client_id         | uuid                     | NO          | null           |
| integration_tokens         | provider                | text                     | YES         | null           |
| integration_tokens         | access_token_encrypted  | text                     | YES         | null           |
| integration_tokens         | refresh_token_encrypted | text                     | YES         | null           |
| integration_tokens         | token_type              | text                     | YES         | null           |
| integration_tokens         | expires_at              | timestamp with time zone | YES         | null           |
| integration_tokens         | scopes                  | jsonb                    | YES         | null           |
| integration_tokens         | metadata                | jsonb                    | YES         | null           |
| integration_tokens         | created_at              | timestamp with time zone | YES         | null           |