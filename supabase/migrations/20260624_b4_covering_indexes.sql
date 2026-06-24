-- B4: Covering indexes for FK client_id on hot-path tables
-- Issue #121 — Performance Phase: P1 bottlenecks

CREATE INDEX CONCURRENTLY idx_shared_business_memory_client_covering
    ON shared_business_memory (client_id)
    INCLUDE (entity_type, entity_name, updated_at);

CREATE INDEX CONCURRENTLY idx_shared_memory_links_client_covering
    ON shared_memory_links (client_id)
    INCLUDE (source_entity_type, source_entity_name, link_type);

CREATE INDEX CONCURRENTLY idx_agent_messages_client_covering
    ON agent_messages (client_id)
    INCLUDE (created_at, role);

CREATE INDEX CONCURRENTLY idx_integration_tokens_client_covering
    ON integration_tokens (client_id)
    INCLUDE (provider, expires_at);
