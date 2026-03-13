-- Migration: Seed initial standalone agent catalog entries
-- Purpose: Populate agent_catalog with 3 starter agent types
-- Date: 2026-03-11

INSERT INTO public.agent_catalog (name, slug, description, category, icon, agent_config, prompt_name, required_context, required_files, requires_google, tier_required)
VALUES
    (
        'Analista de Dados',
        'data-analyst',
        'Analisa arquivos CSV com SQL avançado (JOINs, agregações, window functions). Exporta resultados para Google Sheets.',
        'analytics',
        'BarChart2',
        '{
            "name": "data_analyst",
            "role": "Data Analysis Specialist",
            "elicitation_strategy": "structured_collection",
            "enabled_tools": ["execute_csv_query", "list_csv_datasets", "write_to_sheet", "create_spreadsheet_with_data"],
            "max_turns": 25,
            "model": "openai:gpt-4o"
        }'::JSONB,
        'standalone/data-analyst',
        '[
            {"field": "company_name", "type": "text", "required": true, "label": "Nome da empresa", "prompt_hint": "Qual o nome da sua empresa?"},
            {"field": "industry", "type": "text", "required": true, "label": "Setor de atuação", "prompt_hint": "Em qual setor sua empresa atua?"},
            {"field": "analysis_goals", "type": "text", "required": false, "label": "Objetivos de análise", "prompt_hint": "Quais insights você busca nos seus dados?"}
        ]'::JSONB,
        '{
            "csv": {"min": 1, "max": 5, "description": "Arquivos CSV com dados para análise"},
            "text": {"min": 0, "max": 3, "description": "Documentos com contexto adicional (opcional)"}
        }'::JSONB,
        true,
        'BASIC'
    ),
    (
        'Assistente de Conhecimento',
        'knowledge-assistant',
        'Responde perguntas com base em documentos enviados usando busca semântica (RAG). Ideal para manuais, políticas e bases de conhecimento.',
        'knowledge',
        'BookOpen',
        '{
            "name": "knowledge_assistant",
            "role": "Knowledge Base Assistant",
            "elicitation_strategy": "structured_collection",
            "enabled_tools": ["executar_rag_cliente"],
            "max_turns": 20,
            "model": "openai:gpt-4o-mini"
        }'::JSONB,
        'standalone/knowledge-assistant',
        '[
            {"field": "company_name", "type": "text", "required": true, "label": "Nome da empresa", "prompt_hint": "Qual o nome da sua empresa?"},
            {"field": "knowledge_domain", "type": "text", "required": true, "label": "Domínio do conhecimento", "prompt_hint": "Sobre qual assunto são os documentos? (ex: RH, vendas, suporte técnico)"},
            {"field": "target_audience", "type": "text", "required": false, "label": "Público-alvo", "prompt_hint": "Quem vai usar este assistente? (ex: equipe interna, clientes)"}
        ]'::JSONB,
        '{
            "csv": {"min": 0, "max": 0, "description": ""},
            "text": {"min": 1, "max": 10, "description": "Documentos para base de conhecimento (PDF, TXT, DOCX, MD)"}
        }'::JSONB,
        false,
        'BASIC'
    ),
    (
        'Gerador de Relatórios',
        'report-generator',
        'Combina análise de dados CSV com conhecimento de documentos para gerar relatórios completos. Exporta para Google Sheets.',
        'reporting',
        'FileSpreadsheet',
        '{
            "name": "report_generator",
            "role": "Report Generator",
            "elicitation_strategy": "structured_collection",
            "enabled_tools": ["executar_rag_cliente", "execute_csv_query", "list_csv_datasets", "write_to_sheet"],
            "max_turns": 30,
            "model": "openai:gpt-4o"
        }'::JSONB,
        'standalone/report-generator',
        '[
            {"field": "company_name", "type": "text", "required": true, "label": "Nome da empresa", "prompt_hint": "Qual o nome da sua empresa?"},
            {"field": "report_type", "type": "text", "required": true, "label": "Tipo de relatório", "prompt_hint": "Que tipo de relatório você precisa? (ex: mensal de vendas, análise financeira, performance)"},
            {"field": "kpi_targets", "type": "text", "required": false, "label": "Metas / KPIs", "prompt_hint": "Existem metas ou KPIs específicos que devem aparecer no relatório?"},
            {"field": "report_period", "type": "text", "required": false, "label": "Período do relatório", "prompt_hint": "Qual período o relatório deve cobrir?"}
        ]'::JSONB,
        '{
            "csv": {"min": 1, "max": 5, "description": "Arquivos CSV com dados para o relatório"},
            "text": {"min": 0, "max": 5, "description": "Documentos com contexto ou templates (opcional)"}
        }'::JSONB,
        true,
        'BASIC'
    );
