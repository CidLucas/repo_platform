-- Migration: Add Document Intelligence Agent to catalog
-- Purpose: Agent for structured extraction, time series, and KB persistence from documents
-- Date: 2026-03-21

INSERT INTO public.agent_catalog (name, slug, description, category, icon, agent_config, prompt_name, required_context, required_files, requires_google, tier_required)
VALUES (
    'Document Intelligence',
    'document-intelligence',
    'Reads uploaded documents, extracts structured data (tables, metrics, fields), compiles time series with trend analysis, and saves results to the knowledge base.',
    'data_analysis',
    'FileSearch',
    '{
        "name": "document_intelligence",
        "role": "Document Analysis & Extraction Specialist",
        "elicitation_strategy": "data_analysis",
        "enabled_tools": [
            "executar_rag_cliente",
            "extract_structured_data",
            "compile_time_series",
            "write_summary_to_kb"
        ],
        "max_turns": 30,
        "model": "deepseek-v3.1:671b"
    }'::JSONB,
    'standalone/document-intelligence',
    '[
        {
            "field": "analysis_objective",
            "type": "text",
            "required": true,
            "label": "What is the main objective of the analysis?",
            "prompt_hint": "Ask for the specific goal: summarize, extract data, compare across periods, etc."
        },
        {
            "field": "document_type",
            "type": "select",
            "required": true,
            "label": "Type of documents",
            "prompt_hint": "Understand what kind of documents are being analyzed. Options: financial_reports, contracts, research_papers, operational_reports, mixed"
        },
        {
            "field": "extraction_fields",
            "type": "text",
            "required": false,
            "label": "Specific fields to extract",
            "prompt_hint": "Ask what specific data points they want extracted (e.g., revenue, dates, names, KPIs)"
        },
        {
            "field": "time_period",
            "type": "text",
            "required": false,
            "label": "Time period of interest",
            "prompt_hint": "Ask if they want to compare across time periods (e.g., 2024 vs 2025)"
        },
        {
            "field": "output_format",
            "type": "select",
            "required": true,
            "label": "Desired output format",
            "prompt_hint": "How should the results be presented? Options: summary, structured_table, time_series, report"
        }
    ]'::JSONB,
    '{
        "document": {
            "min": 1,
            "max": 20,
            "description": "Upload PDF, DOCX, TXT, or MD documents for analysis"
        }
    }'::JSONB,
    false,
    'PROFESSIONAL'
);
