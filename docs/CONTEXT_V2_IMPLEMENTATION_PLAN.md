# Context 2.0 Implementation Plan

## Executive Summary

This document outlines the complete implementation plan for the **Modular Client Context System** (Context 2.0) - a comprehensive upgrade to how client context is stored, retrieved, and injected into AI agents.

### Goals
1. **Richer client context** — Replace single `prompt_base` text with modular, structured sections
2. **Selective injection** — Different agent nodes receive only the context they need
3. **Security by design** — Clear separation between LLM-safe and internal data
4. **Dynamic vs static data** — Separate update frequencies (weekly moments vs quarterly profiles)
5. **Scalability** — Standard structure that works for all clients with customization options

### Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1. Database | Add JSONB columns to `clientes_vizu` | ✅ DONE |
| 2. Models | Update `ClienteVizu` with section columns | ✅ DONE |
| 3. Schemas | Pydantic schemas for section validation | ✅ DONE |
| 4. SafeClientContext | Modular context with `get_compiled_context()` | ✅ DONE |
| 5. ContextService | Load sections from DB, include in VizuClientContext | ✅ DONE |
| 6. VizuClientContext | Add `to_safe_context()` conversion method | ✅ DONE |
| 7. Test Data | Polen client populated with all sections | ✅ DONE |
| 8. Agent Integration | Selective context injection per node | ⏳ TODO |
| 9. Admin UI | Dashboard for managing context sections | ⏳ TODO |

---

## Current State Analysis

### What We Have Today

```
clientes_vizu table:
├── client_id (UUID PK)
├── nome_empresa (TEXT)
├── tier (TEXT: "free", "basic", "sme", etc.)
├── prompt_base (TEXT) ← Single string for ALL context
├── enabled_tools (TEXT[])
├── collection_rag (TEXT)
├── horario_funcionamento (JSONB)
└── external_user_id (TEXT)
```

**Problems:**
1. `prompt_base` is a single string — no structure, no sections
2. No company profile, brand voice, or market context
3. No dynamic "current moment" that can be updated frequently
4. No selective injection — all context goes to all nodes
5. Missing critical business context for quality AI responses

### What We Want

```
clientes_vizu table (Context 2.0 - FINAL):
├── client_id (UUID PK)
├── external_user_id (TEXT UNIQUE)
├── nome_empresa (TEXT)
├── cpf_cnpj (TEXT)
├── tier (TEXT: BASIC, SME, ENTERPRISE)
│
├── company_profile (JSONB)     ← Core identity
├── brand_voice (JSONB)         ← Communication style
├── product_catalog (JSONB)     ← Products/services
├── target_audience (JSONB)     ← ICP, personas
├── market_context (JSONB)      ← Competitors, regulations
├── current_moment (JSONB)      ← Weekly priorities/challenges
├── team_structure (JSONB)      ← Contacts, hours
├── policies (JSONB)            ← Rules, guardrails
├── data_schema (JSONB)         ← Available data
├── available_tools (JSONB)     ← Tool config, default prompt
├── client_custom (JSONB)       ← Extension point
│
├── created_at (TIMESTAMPTZ)
├── updated_at (TIMESTAMPTZ)
│
└── LEGACY (deprecated):
    ├── prompt_base (TEXT)
    ├── enabled_tools (TEXT[])
    ├── horario_funcionamento (JSONB)
    └── collection_rag (TEXT)
```

---

## Architecture Overview

### Single Table Design (Simpler)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           clientes_vizu                                  │
│  (All context embedded as JSONB columns - no separate table)            │
├─────────────────────────────────────────────────────────────────────────┤
│  client_id        │ UUID PK                                             │
│  external_user_id │ TEXT (OAuth mapping)                                │
│  nome_empresa     │ TEXT                                                │
│  cpf_cnpj         │ TEXT                                                │
│  tier             │ TEXT (BASIC/SME/ENTERPRISE)                         │
│  ─────────────────────────────────────────────────────────────────────  │
│  company_profile  │ JSONB  ← {"legal_name": "...", "mission": "..."}    │
│  brand_voice      │ JSONB  ← {"tone": "...", "phrases_to_avoid": [...]} │
│  current_moment   │ JSONB  ← {"priorities": [...], "challenges": [...]} │
│  ... (8 more)     │ JSONB                                               │
│  ─────────────────────────────────────────────────────────────────────  │
│  created_at       │ TIMESTAMPTZ                                         │
│  updated_at       │ TIMESTAMPTZ                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why embedded JSONB instead of separate table?**
- Simpler queries (single SELECT)
- No JOINs needed for context loading
- All context in one row = faster cache
- Easier to update (single UPDATE statement)
- PostgreSQL JSONB is highly optimized

### Section Types (Enum)

```python
class ContextSection(Enum):
    # Core Identity (update: quarterly)
    COMPANY_PROFILE = "company_profile"      # Mission, vision, values
    BRAND_VOICE = "brand_voice"              # Tone, style, phrases

    # Business (update: monthly)
    PRODUCT_CATALOG = "product_catalog"      # Products/services offered
    TARGET_AUDIENCE = "target_audience"      # ICP, personas, pain points
    MARKET_CONTEXT = "market_context"        # Competitors, differentiators

    # Operations (update: weekly)
    CURRENT_MOMENT = "current_moment"        # Priorities, challenges, metrics
    TEAM_STRUCTURE = "team_structure"        # Key contacts, roles
    POLICIES_GUARDRAILS = "policies"         # Rules, limits, approval flows

    # Technical (update: on change)
    DATA_SCHEMA = "data_schema"              # Available tables, formats
    AVAILABLE_TOOLS = "available_tools"      # Tool descriptions, limits

    # Custom (client-specific)
    CLIENT_CUSTOM = "client_custom"          # Extension point
```

### Context Injection Pattern

```
                    ┌─────────────────┐
                    │  Agent Request  │
                    └────────┬────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                     ContextService                              │
│  get_client_context_by_id(client_id) → VizuClientContext       │
│  get_context_sections(client_id, sections) → dict[section]     │
└────────────────────────────────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   init_node     │ │  respond_node   │ │  tool_node      │
│                 │ │                 │ │                 │
│ Needs:          │ │ Needs:          │ │ Needs:          │
│ - basic_info    │ │ - brand_voice   │ │ - data_schema   │
│ - tier          │ │ - current_moment│ │ - tools_config  │
│ - tools_list    │ │ - policies      │ │ - client_id     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Implementation Phases

### Phase 1: Database Schema (Week 1)

#### 1.1 Add Context Section Columns to clientes_vizu

```sql
-- Migration: add_context_sections_to_clientes_vizu.sql
-- Adds JSONB columns for each context section directly on the clientes_vizu table

-- 1. Add identification column
ALTER TABLE clientes_vizu
ADD COLUMN IF NOT EXISTS cpf_cnpj TEXT;

-- 2. Add context section columns (JSONB)
ALTER TABLE clientes_vizu
ADD COLUMN IF NOT EXISTS company_profile JSONB,
ADD COLUMN IF NOT EXISTS brand_voice JSONB,
ADD COLUMN IF NOT EXISTS product_catalog JSONB,
ADD COLUMN IF NOT EXISTS target_audience JSONB,
ADD COLUMN IF NOT EXISTS market_context JSONB,
ADD COLUMN IF NOT EXISTS current_moment JSONB,
ADD COLUMN IF NOT EXISTS team_structure JSONB,
ADD COLUMN IF NOT EXISTS policies JSONB,
ADD COLUMN IF NOT EXISTS data_schema JSONB,
ADD COLUMN IF NOT EXISTS available_tools JSONB,
ADD COLUMN IF NOT EXISTS client_custom JSONB;

-- 3. Add comments for documentation
COMMENT ON COLUMN clientes_vizu.company_profile IS 'Company identity: mission, vision, values, archetype';
COMMENT ON COLUMN clientes_vizu.brand_voice IS 'Communication style: tone, phrases to use/avoid';
COMMENT ON COLUMN clientes_vizu.product_catalog IS 'Products and services offered';
COMMENT ON COLUMN clientes_vizu.target_audience IS 'ICP, buyer personas, pain points';
COMMENT ON COLUMN clientes_vizu.market_context IS 'Competitors, differentiators, regulations';
COMMENT ON COLUMN clientes_vizu.current_moment IS 'Current priorities, challenges, wins (update weekly)';
COMMENT ON COLUMN clientes_vizu.team_structure IS 'Key contacts, escalation paths, business hours';
COMMENT ON COLUMN clientes_vizu.policies IS 'Rules, guardrails, approval workflows';
COMMENT ON COLUMN clientes_vizu.data_schema IS 'Available data tables, formats, key fields';
COMMENT ON COLUMN clientes_vizu.available_tools IS 'Tool config: enabled tools, limits, default prompt';
COMMENT ON COLUMN clientes_vizu.client_custom IS 'Client-specific custom context';

-- 4. Mark legacy columns as deprecated (comments only, keep for backward compat)
COMMENT ON COLUMN clientes_vizu.prompt_base IS 'DEPRECATED: Use available_tools.default_system_prompt';
COMMENT ON COLUMN clientes_vizu.enabled_tools IS 'DEPRECATED: Use available_tools.enabled_tool_names';
COMMENT ON COLUMN clientes_vizu.horario_funcionamento IS 'DEPRECATED: Use team_structure.business_hours';

-- 5. Create GIN indexes for JSONB columns (for fast queries on nested fields)
CREATE INDEX IF NOT EXISTS idx_clientes_vizu_company_profile ON clientes_vizu USING GIN (company_profile);
CREATE INDEX IF NOT EXISTS idx_clientes_vizu_available_tools ON clientes_vizu USING GIN (available_tools);
CREATE INDEX IF NOT EXISTS idx_clientes_vizu_current_moment ON clientes_vizu USING GIN (current_moment);
```

### Phase 2: Models ✅ DONE

The `ClienteVizu` model in `vizu_models` has been updated with all context section columns.

**File:** `libs/vizu_models/src/vizu_models/cliente_vizu.py`

Key fields:
- `cpf_cnpj` - Client document (CPF/CNPJ)
- `company_profile` - JSONB
- `brand_voice` - JSONB
- `product_catalog` - JSONB
- `target_audience` - JSONB
- `market_context` - JSONB
- `current_moment` - JSONB
- `team_structure` - JSONB
- `policies` - JSONB
- `data_schema` - JSONB
- `available_tools` - JSONB
- `client_custom` - JSONB

Helper methods:
- `get_enabled_tools_list()` - Prefers `available_tools.enabled_tool_names`, falls back to legacy
- `get_default_prompt()` - Prefers `available_tools.default_system_prompt`, falls back to `prompt_base`
- `get_business_hours()` - Prefers `team_structure.business_hours`, falls back to legacy

### Phase 3: Context Schemas ✅ DONE

**File:** `libs/vizu_models/src/vizu_models/context_schemas.py`

Pydantic models for validating section content:
- `CompanyProfile` - legal_name, mission, vision, core_values
- `BrandVoice` - tone, key_phrases_to_use, phrases_to_avoid
- `ProductCatalog` - products, services, pricing_tiers
- `TargetAudience` - ICP, buyer_personas, pain_points
- `MarketContext` - competitors, differentiators, regulations
- `CurrentMoment` - priorities, challenges, wins, metrics
- `TeamStructure` - key_contacts, escalation_path, business_hours
- `Policies` - communication_rules, approval_requirements, red_flags
- `DataSchema` - available_tables, key_fields, data_formats
- `AvailableTools` - enabled_tool_names, default_system_prompt, limits

### Phase 4: SafeClientContext ✅ DONE

**File:** `libs/vizu_models/src/vizu_models/safe_client_context.py`

Updated to support modular sections:
- Each section is an optional field
- `loaded_sections` tracks which sections are populated
- `get_compiled_context(sections)` formats sections for prompt injection
- `get_section(section_type)` retrieves individual sections

### Phase 2: Models & Enums (Week 1)

#### 2.1 New Enums in vizu_models

**File:** `libs/vizu_models/src/vizu_models/enums.py`

```python
"""Enums for the Vizu platform."""

from enum import Enum


class ClientTier(Enum):
    """
    Client tiers control tool access and usage limits.

    Supports comparison: FREE < BASIC < SME < PREMIUM < ENTERPRISE
    """
    FREE = "FREE"
    BASIC = "BASIC"
    SME = "SME"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"

    def __lt__(self, other):
        if not isinstance(other, ClientTier):
            return NotImplemented
        order = list(ClientTier)
        return order.index(self) < order.index(other)

    def __le__(self, other):
        return self == other or self < other


class ContextSection(Enum):
    """
    Sections of the modular client context.

    Each section can be injected independently into agent nodes.
    Grouped by typical update frequency.
    """
    # Core Identity (quarterly updates)
    COMPANY_PROFILE = "company_profile"
    BRAND_VOICE = "brand_voice"

    # Business (monthly updates)
    PRODUCT_CATALOG = "product_catalog"
    TARGET_AUDIENCE = "target_audience"
    MARKET_CONTEXT = "market_context"

    # Operations (weekly updates)
    CURRENT_MOMENT = "current_moment"
    TEAM_STRUCTURE = "team_structure"
    POLICIES = "policies"

    # Technical (on-change updates)
    DATA_SCHEMA = "data_schema"
    AVAILABLE_TOOLS = "available_tools"

    # Custom extension point
    CLIENT_CUSTOM = "client_custom"
```

#### 2.2 Context Section Model

**File:** `libs/vizu_models/src/vizu_models/client_context_section.py`

```python
"""Client context section models."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as pgUUID, ENUM as pgENUM
from sqlmodel import Column, Field as SQLField, SQLModel

from .enums import ContextSection


class ClientContextSectionBase(SQLModel):
    """Base model for context sections."""
    section_type: ContextSection
    content: dict[str, Any] = SQLField(default_factory=dict)
    is_active: bool = True
    version: int = 1


class ClientContextSection(ClientContextSectionBase, table=True):
    """Database model for client context sections."""
    __tablename__ = "client_context_sections"

    id: uuid.UUID | None = SQLField(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True)
    )

    client_id: uuid.UUID = SQLField(
        sa_column=Column(
            pgUUID(as_uuid=True),
            nullable=False,
            index=True
        )
    )

    section_type: ContextSection = SQLField(
        sa_column=Column(
            pgENUM(ContextSection, name="context_section_type", create_type=False),
            nullable=False
        )
    )

    content: dict[str, Any] = SQLField(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}")
    )

    is_active: bool = SQLField(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default="true")
    )

    version: int = SQLField(
        default=1,
        sa_column=Column(Integer, nullable=False, server_default="1")
    )

    last_updated_at: datetime | None = SQLField(default=None)
    updated_by: str | None = SQLField(default=None, sa_column=Column(Text))
    created_at: datetime | None = SQLField(default=None)


class ClientContextSectionCreate(BaseModel):
    """Schema for creating a context section."""
    client_id: uuid.UUID
    section_type: ContextSection
    content: dict[str, Any]
    updated_by: str | None = None


class ClientContextSectionUpdate(BaseModel):
    """Schema for updating a context section."""
    content: dict[str, Any]
    updated_by: str | None = None


class ClientContextSectionRead(ClientContextSectionBase):
    """Schema for reading a context section."""
    id: uuid.UUID
    client_id: uuid.UUID
    last_updated_at: datetime | None
    updated_by: str | None
    created_at: datetime | None
```

#### 2.3 Section Content Schemas

**File:** `libs/vizu_models/src/vizu_models/context_schemas.py`

```python
"""
JSON schemas for context section content.

These define the structure of each section's JSONB content.
Used for validation, documentation, and type hints.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CompanyProfile(BaseModel):
    """Section: COMPANY_PROFILE - Who we are and where we're going."""
    legal_name: str | None = None
    trading_name: str | None = None
    business_archetype: str | None = Field(
        None,
        description="e.g., 'B2B SaaS', 'E-commerce', 'Environmental Services'"
    )
    industry: str | None = None
    mission: str | None = None
    vision: str | None = None
    core_values: list[str] = Field(default_factory=list)
    founding_year: int | None = None
    headquarters_city: str | None = None
    employee_count_range: str | None = Field(
        None,
        description="e.g., '1-10', '11-50', '51-200', '201-500', '500+'"
    )


class BrandVoice(BaseModel):
    """Section: BRAND_VOICE - How we communicate."""
    tone: str | None = Field(
        None,
        description="e.g., 'professional but approachable', 'technical and precise'"
    )
    personality_traits: list[str] = Field(
        default_factory=list,
        description="e.g., ['innovative', 'trustworthy', 'helpful']"
    )
    language: str = Field(
        default="pt-BR",
        description="Primary language code"
    )
    formality_level: str | None = Field(
        None,
        description="'formal', 'semi-formal', 'casual'"
    )
    key_phrases_to_use: list[str] = Field(
        default_factory=list,
        description="Phrases that reinforce brand identity"
    )
    phrases_to_avoid: list[str] = Field(
        default_factory=list,
        description="Phrases that damage brand (e.g., greenwashing terms)"
    )
    communication_guidelines: str | None = Field(
        None,
        description="Free-form guidelines for AI responses"
    )


class ProductService(BaseModel):
    """Single product or service in the catalog."""
    name: str
    description: str | None = None
    category: str | None = None
    target_segment: str | None = None
    key_features: list[str] = Field(default_factory=list)
    pricing_model: str | None = Field(
        None,
        description="e.g., 'subscription', 'one-time', 'usage-based'"
    )


class ProductCatalog(BaseModel):
    """Section: PRODUCT_CATALOG - What we offer."""
    products: list[ProductService] = Field(default_factory=list)
    services: list[ProductService] = Field(default_factory=list)
    flagship_offering: str | None = Field(
        None,
        description="Main product/service to emphasize"
    )


class TargetAudience(BaseModel):
    """Section: TARGET_AUDIENCE - Who we serve."""
    primary_audience: str | None = Field(
        None,
        description="Main target customer description"
    )
    ideal_customer_profile: str | None = Field(
        None,
        description="Detailed ICP description"
    )
    buyer_personas: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of persona objects with role, pain points, goals"
    )
    industries_served: list[str] = Field(default_factory=list)
    company_size_target: str | None = None
    geographic_focus: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(
        default_factory=list,
        description="Common problems our audience faces"
    )


class MarketContext(BaseModel):
    """Section: MARKET_CONTEXT - Where we compete."""
    key_competitors: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {name, positioning} objects"
    )
    differentiators: list[str] = Field(
        default_factory=list,
        description="What makes us unique"
    )
    market_position: str | None = Field(
        None,
        description="e.g., 'market leader', 'challenger', 'niche specialist'"
    )
    regulatory_environment: str | None = Field(
        None,
        description="Relevant regulations (e.g., LGPD, PNRS)"
    )
    market_trends: list[str] = Field(
        default_factory=list,
        description="Current trends affecting the market"
    )


class CurrentMoment(BaseModel):
    """
    Section: CURRENT_MOMENT - What we're focusing on NOW.

    This is the most dynamic section, updated weekly.
    """
    stage: str | None = Field(
        None,
        description="'startup', 'growth', 'scaling', 'maturity'"
    )
    current_priorities: list[str] = Field(
        default_factory=list,
        description="Top 3-5 priorities right now"
    )
    current_challenges: list[str] = Field(
        default_factory=list,
        description="Main obstacles being faced"
    )
    recent_wins: list[str] = Field(
        default_factory=list,
        description="Recent achievements to celebrate"
    )
    key_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Current KPIs (non-sensitive aggregates only)"
    )
    active_campaigns: list[str] = Field(
        default_factory=list,
        description="Marketing/sales campaigns in progress"
    )
    upcoming_events: list[str] = Field(
        default_factory=list,
        description="Events, launches, deadlines"
    )
    week_of: str | None = Field(
        None,
        description="Week this moment refers to (YYYY-WW)"
    )


class TeamMember(BaseModel):
    """Key team member for context."""
    role: str
    name: str | None = None
    contact_preference: str | None = None


class TeamStructure(BaseModel):
    """Section: TEAM_STRUCTURE - Who to contact."""
    key_contacts: list[TeamMember] = Field(default_factory=list)
    escalation_path: list[str] = Field(
        default_factory=list,
        description="Who to escalate to and when"
    )
    communication_channels: dict[str, str] = Field(
        default_factory=dict,
        description="e.g., {'urgent': 'Slack', 'formal': 'email'}"
    )


class Policies(BaseModel):
    """Section: POLICIES - Rules and guardrails."""
    communication_rules: list[str] = Field(
        default_factory=list,
        description="What to say/not say"
    )
    operational_limits: list[str] = Field(
        default_factory=list,
        description="What actions are restricted"
    )
    approval_requirements: dict[str, list[str]] = Field(
        default_factory=dict,
        description="{'autonomous': [...], 'requires_approval': [...]}"
    )
    red_flags: list[str] = Field(
        default_factory=list,
        description="Situations that should trigger alerts"
    )
    compliance_notes: str | None = None


class DataSchema(BaseModel):
    """Section: DATA_SCHEMA - What data is available."""
    available_tables: list[str] = Field(default_factory=list)
    key_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Field name → description mapping"
    )
    data_formats: dict[str, str] = Field(
        default_factory=dict,
        description="e.g., {'dates': 'DD/MM/YYYY', 'currency': 'BRL'}"
    )
    data_freshness: str | None = Field(
        None,
        description="How often data is updated"
    )


class AvailableTools(BaseModel):
    """Section: AVAILABLE_TOOLS - What the AI can do."""
    tier: str = "BASIC"
    enabled_tool_names: list[str] = Field(default_factory=list)
    tool_descriptions: dict[str, str] = Field(
        default_factory=dict,
        description="Tool name → description"
    )
    autonomous_actions: list[str] = Field(
        default_factory=list,
        description="Actions AI can take without approval"
    )
    restricted_actions: list[str] = Field(
        default_factory=list,
        description="Actions that require human approval"
    )
    usage_limits: dict[str, Any] = Field(
        default_factory=dict,
        description="Rate limits, quotas, etc."
    )


# Mapping from section type to schema class
SECTION_SCHEMAS = {
    "company_profile": CompanyProfile,
    "brand_voice": BrandVoice,
    "product_catalog": ProductCatalog,
    "target_audience": TargetAudience,
    "market_context": MarketContext,
    "current_moment": CurrentMoment,
    "team_structure": TeamStructure,
    "policies": Policies,
    "data_schema": DataSchema,
    "available_tools": AvailableTools,
}
```

### Phase 3: Enhanced SafeClientContext (Week 2)

#### 3.1 Updated SafeClientContext

**File:** `libs/vizu_models/src/vizu_models/safe_client_context.py` (updated)

```python
"""
SafeClientContext - Modular context safe for LLM exposure.

Context 2.0: Supports selective section injection for different agent nodes.
"""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import ClientTier, ContextSection
from .context_schemas import (
    CompanyProfile,
    BrandVoice,
    ProductCatalog,
    TargetAudience,
    MarketContext,
    CurrentMoment,
    TeamStructure,
    Policies,
    DataSchema,
    AvailableTools,
)


class SafeClientContext(BaseModel):
    """
    Modular client context safe for LLM exposure.

    Context 2.0 Features:
    - Sections can be loaded/injected independently
    - Immutable to prevent accidental modifications
    - No sensitive data (credentials, internal IDs)

    Usage:
        # Full context
        context.get_compiled_context()

        # Selective injection
        context.get_compiled_context([
            ContextSection.BRAND_VOICE,
            ContextSection.CURRENT_MOMENT,
        ])
    """

    model_config = ConfigDict(frozen=True)

    # ===== BASIC IDENTITY (always injected) =====
    nome_empresa: str
    tier: ClientTier = ClientTier.BASIC
    enabled_tools: list[str] = Field(default_factory=list)

    # ===== LEGACY FIELDS (backward compatibility) =====
    prompt_base: str | None = None
    horario_funcionamento: dict[str, Any] | None = None
    collection_rag: str | None = None

    # ===== MODULAR SECTIONS (Context 2.0) =====
    company_profile: CompanyProfile | None = None
    brand_voice: BrandVoice | None = None
    product_catalog: ProductCatalog | None = None
    target_audience: TargetAudience | None = None
    market_context: MarketContext | None = None
    current_moment: CurrentMoment | None = None
    team_structure: TeamStructure | None = None
    policies: Policies | None = None
    data_schema: DataSchema | None = None
    available_tools_config: AvailableTools | None = None
    client_custom: dict[str, Any] | None = None

    # ===== SECTION METADATA =====
    loaded_sections: list[ContextSection] = Field(default_factory=list)

    def get_section(self, section: ContextSection) -> BaseModel | dict | None:
        """Get a specific section by type."""
        section_map = {
            ContextSection.COMPANY_PROFILE: self.company_profile,
            ContextSection.BRAND_VOICE: self.brand_voice,
            ContextSection.PRODUCT_CATALOG: self.product_catalog,
            ContextSection.TARGET_AUDIENCE: self.target_audience,
            ContextSection.MARKET_CONTEXT: self.market_context,
            ContextSection.CURRENT_MOMENT: self.current_moment,
            ContextSection.TEAM_STRUCTURE: self.team_structure,
            ContextSection.POLICIES: self.policies,
            ContextSection.DATA_SCHEMA: self.data_schema,
            ContextSection.AVAILABLE_TOOLS: self.available_tools_config,
            ContextSection.CLIENT_CUSTOM: self.client_custom,
        }
        return section_map.get(section)

    def get_compiled_context(
        self,
        sections: list[ContextSection] | None = None
    ) -> str:
        """
        Compile context sections into a formatted string for LLM injection.

        Args:
            sections: Specific sections to include. If None, includes all loaded sections.

        Returns:
            Formatted context string ready for prompt injection.
        """
        if sections is None:
            sections = self.loaded_sections or list(ContextSection)

        parts = [f"# Contexto: {self.nome_empresa}"]
        parts.append(f"Tier: {self.tier.value}")

        for section in sections:
            content = self.get_section(section)
            if content is None:
                continue

            section_text = self._format_section(section, content)
            if section_text:
                parts.append(section_text)

        # Legacy: Include prompt_base if present and no sections loaded
        if self.prompt_base and not self.loaded_sections:
            parts.append(f"\n## Instruções Adicionais\n{self.prompt_base}")

        return "\n\n".join(parts)

    def _format_section(self, section: ContextSection, content: Any) -> str:
        """Format a single section for prompt injection."""
        if content is None:
            return ""

        headers = {
            ContextSection.COMPANY_PROFILE: "## Perfil da Empresa",
            ContextSection.BRAND_VOICE: "## Voz da Marca",
            ContextSection.PRODUCT_CATALOG: "## Produtos e Serviços",
            ContextSection.TARGET_AUDIENCE: "## Público-Alvo",
            ContextSection.MARKET_CONTEXT: "## Contexto de Mercado",
            ContextSection.CURRENT_MOMENT: "## Momento Atual",
            ContextSection.TEAM_STRUCTURE: "## Estrutura da Equipe",
            ContextSection.POLICIES: "## Políticas e Limites",
            ContextSection.DATA_SCHEMA: "## Dados Disponíveis",
            ContextSection.AVAILABLE_TOOLS: "## Ferramentas Disponíveis",
            ContextSection.CLIENT_CUSTOM: "## Contexto Personalizado",
        }

        header = headers.get(section, f"## {section.value}")

        if isinstance(content, BaseModel):
            content_dict = content.model_dump(exclude_none=True)
        else:
            content_dict = content

        lines = [header]
        for key, value in content_dict.items():
            if value is None or value == [] or value == {}:
                continue

            # Format key nicely
            key_formatted = key.replace("_", " ").title()

            if isinstance(value, list):
                lines.append(f"**{key_formatted}:**")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"  - {item}")
                    else:
                        lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"**{key_formatted}:** {value}")
            else:
                lines.append(f"**{key_formatted}:** {value}")

        return "\n".join(lines) if len(lines) > 1 else ""


class InternalClientContext(BaseModel):
    """
    Internal context with sensitive data - NEVER exposed to LLM.

    Contains the client ID needed for database operations, tool injection, etc.
    """

    id: uuid.UUID
    safe_context: SafeClientContext

    @classmethod
    def from_vizu_client_context(
        cls,
        ctx: Any,
        sections: dict[ContextSection, dict] | None = None
    ) -> "InternalClientContext":
        """
        Create from VizuClientContext with optional pre-loaded sections.

        Args:
            ctx: VizuClientContext from database
            sections: Pre-loaded section content {section_type: content}
        """
        # Get enabled tools
        enabled_tools = []
        if hasattr(ctx, 'get_enabled_tools_list'):
            enabled_tools = ctx.get_enabled_tools_list()
        elif hasattr(ctx, 'enabled_tools') and ctx.enabled_tools:
            enabled_tools = list(ctx.enabled_tools) if isinstance(ctx.enabled_tools, list) else []

        # Get tier
        tier_value = ClientTier.BASIC
        if hasattr(ctx, 'tier') and ctx.tier:
            tier_str = ctx.tier.value if hasattr(ctx.tier, 'value') else str(ctx.tier).upper()
            try:
                tier_value = ClientTier(tier_str)
            except ValueError:
                tier_value = ClientTier.BASIC

        # Build section kwargs
        section_kwargs = {}
        loaded_sections = []

        if sections:
            from .context_schemas import SECTION_SCHEMAS

            for section_type, content in sections.items():
                if content is None:
                    continue

                # Map section type to field name
                field_name = section_type.value
                if section_type == ContextSection.AVAILABLE_TOOLS:
                    field_name = "available_tools_config"

                # Validate content against schema if available
                schema_class = SECTION_SCHEMAS.get(section_type.value)
                if schema_class:
                    try:
                        validated = schema_class.model_validate(content)
                        section_kwargs[field_name] = validated
                        loaded_sections.append(section_type)
                    except Exception:
                        # Store raw dict if validation fails
                        section_kwargs[field_name] = content
                        loaded_sections.append(section_type)
                else:
                    section_kwargs[field_name] = content
                    loaded_sections.append(section_type)

        safe = SafeClientContext(
            nome_empresa=ctx.nome_empresa,
            tier=tier_value,
            enabled_tools=enabled_tools,
            prompt_base=getattr(ctx, 'prompt_base', None),
            horario_funcionamento=getattr(ctx, 'horario_funcionamento', None),
            collection_rag=getattr(ctx, 'collection_rag', None),
            loaded_sections=loaded_sections,
            **section_kwargs,
        )

        return cls(id=ctx.id, safe_context=safe)

    def get_safe_context(self) -> SafeClientContext:
        """Return the LLM-safe context."""
        return self.safe_context

    def get_client_id_for_tools(self) -> str:
        """Return client ID for internal tool injection."""
        return str(self.id)
```

### Phase 4: Context Service Updates (Week 2)

#### 4.1 Add Section Loading to ContextService

**File:** `libs/vizu_context_service/src/vizu_context_service/context_service.py` (additions)

```python
# Add to imports
from vizu_models.enums import ContextSection
from vizu_models.client_context_section import ClientContextSection

class ContextService:
    # ... existing code ...

    SECTION_CACHE_PREFIX = "context:section:"
    SECTION_CACHE_TTL = 600  # 10 minutes for sections

    async def get_context_sections(
        self,
        client_id: UUID,
        sections: list[ContextSection] | None = None,
    ) -> dict[ContextSection, dict]:
        """
        Fetch specific context sections for a client.

        Args:
            client_id: Client UUID
            sections: List of sections to fetch. If None, fetches all.

        Returns:
            Dict mapping section type to content
        """
        if sections is None:
            sections = list(ContextSection)

        result = {}
        sections_to_fetch = []

        # 1. Check cache for each section
        for section in sections:
            cache_key = f"{self.SECTION_CACHE_PREFIX}{client_id}:{section.value}"
            cached = await asyncio.to_thread(self.cache.get_json, cache_key)
            if cached is not None:
                result[section] = cached
            else:
                sections_to_fetch.append(section)

        if not sections_to_fetch:
            return result

        # 2. Fetch missing sections from database
        if self._use_supabase:
            section_values = [s.value for s in sections_to_fetch]
            response = get_supabase_client().table("client_context_sections").select(
                "section_type, content"
            ).eq(
                "client_id", str(client_id)
            ).eq(
                "is_active", True
            ).in_(
                "section_type", section_values
            ).execute()

            for row in response.data:
                section_type = ContextSection(row["section_type"])
                content = row["content"]
                result[section_type] = content

                # Cache the section
                cache_key = f"{self.SECTION_CACHE_PREFIX}{client_id}:{section_type.value}"
                await asyncio.to_thread(
                    self.cache.set_json,
                    cache_key,
                    content,
                    self.SECTION_CACHE_TTL
                )

        return result

    async def get_client_context_with_sections(
        self,
        client_id: UUID,
        sections: list[ContextSection] | None = None,
    ) -> "InternalClientContext":
        """
        Get full client context with specified sections loaded.

        This is the primary method for Context 2.0 - fetches base client
        data plus requested modular sections.

        Args:
            client_id: Client UUID
            sections: Sections to load. If None, loads all available.

        Returns:
            InternalClientContext with safe_context populated with sections
        """
        from vizu_models import InternalClientContext

        # 1. Get base client context (legacy)
        base_context = await self.get_client_context_by_id(client_id)
        if base_context is None:
            raise ValueError(f"Client not found: {client_id}")

        # 2. Fetch requested sections
        section_data = await self.get_context_sections(client_id, sections)

        # 3. Build internal context with sections
        return InternalClientContext.from_vizu_client_context(
            base_context,
            sections=section_data
        )

    async def upsert_context_section(
        self,
        client_id: UUID,
        section_type: ContextSection,
        content: dict,
        updated_by: str | None = None,
    ) -> dict:
        """
        Create or update a context section.

        If an active section exists, it's updated. Otherwise, a new one is created.
        Invalidates the cache for this section.
        """
        if self._use_supabase:
            client = get_supabase_client()

            # Check if active section exists
            existing = client.table("client_context_sections").select("id").eq(
                "client_id", str(client_id)
            ).eq(
                "section_type", section_type.value
            ).eq(
                "is_active", True
            ).execute()

            if existing.data:
                # Update existing
                response = client.table("client_context_sections").update({
                    "content": content,
                    "updated_by": updated_by,
                }).eq(
                    "id", existing.data[0]["id"]
                ).execute()
            else:
                # Create new
                response = client.table("client_context_sections").insert({
                    "client_id": str(client_id),
                    "section_type": section_type.value,
                    "content": content,
                    "updated_by": updated_by,
                }).execute()

            # Invalidate cache
            cache_key = f"{self.SECTION_CACHE_PREFIX}{client_id}:{section_type.value}"
            await asyncio.to_thread(self.cache.delete, cache_key)

            return response.data[0] if response.data else {}

        raise NotImplementedError("Section management requires Supabase backend")

    def invalidate_section_cache(self, client_id: UUID, section: ContextSection) -> None:
        """Invalidate cache for a specific section."""
        cache_key = f"{self.SECTION_CACHE_PREFIX}{client_id}:{section.value}"
        self.cache.delete(cache_key)

    def invalidate_all_sections_cache(self, client_id: UUID) -> None:
        """Invalidate cache for all sections of a client."""
        for section in ContextSection:
            self.invalidate_section_cache(client_id, section)
```

### Phase 5: Agent Integration (Week 3)

#### 5.1 Node-Specific Context Requirements

**File:** `libs/vizu_agent_framework/src/vizu_agent_framework/context_requirements.py`

```python
"""
Define which context sections each node type needs.

This enables selective injection - nodes only receive relevant context.
"""

from vizu_models.enums import ContextSection


# Node → Required Sections mapping
NODE_CONTEXT_REQUIREMENTS: dict[str, list[ContextSection]] = {
    # Init node: Basic identification and tools
    "init_node": [
        ContextSection.AVAILABLE_TOOLS,
    ],

    # Respond node: Full communication context
    "respond_node": [
        ContextSection.BRAND_VOICE,
        ContextSection.CURRENT_MOMENT,
        ContextSection.POLICIES,
        ContextSection.COMPANY_PROFILE,
    ],

    # Tool execution nodes
    "execute_rag_tool": [
        ContextSection.DATA_SCHEMA,
        ContextSection.COMPANY_PROFILE,
    ],

    "execute_sql_tool": [
        ContextSection.DATA_SCHEMA,
    ],

    # Sales/marketing nodes
    "sales_node": [
        ContextSection.BRAND_VOICE,
        ContextSection.PRODUCT_CATALOG,
        ContextSection.TARGET_AUDIENCE,
        ContextSection.MARKET_CONTEXT,
        ContextSection.CURRENT_MOMENT,
        ContextSection.POLICIES,
    ],

    # Support/triage nodes
    "support_node": [
        ContextSection.BRAND_VOICE,
        ContextSection.POLICIES,
        ContextSection.TEAM_STRUCTURE,
        ContextSection.CURRENT_MOMENT,
    ],

    # Compliance/reporting nodes
    "compliance_node": [
        ContextSection.COMPANY_PROFILE,
        ContextSection.POLICIES,
        ContextSection.DATA_SCHEMA,
        ContextSection.CURRENT_MOMENT,
    ],

    # Default fallback
    "default": [
        ContextSection.BRAND_VOICE,
        ContextSection.CURRENT_MOMENT,
    ],
}


def get_required_sections(node_name: str) -> list[ContextSection]:
    """Get the context sections required by a specific node."""
    return NODE_CONTEXT_REQUIREMENTS.get(
        node_name,
        NODE_CONTEXT_REQUIREMENTS["default"]
    )


def get_all_required_sections(node_names: list[str]) -> list[ContextSection]:
    """Get union of all sections required by multiple nodes."""
    sections = set()
    for node_name in node_names:
        sections.update(get_required_sections(node_name))
    return list(sections)
```

#### 5.2 Update Dynamic Prompt Building

**File:** `services/atendente_core/src/atendente_core/core/nodes.py` (updated)

```python
async def build_dynamic_system_prompt(
    safe_context: SafeClientContext | None,
    available_tools: list[BaseTool],
    cliente_id: UUID | None = None,
    context_service: "ContextService | None" = None,
    node_name: str = "respond_node",
) -> str:
    """
    Build system prompt with Context 2.0 selective injection.

    Args:
        safe_context: Client context (may have sections pre-loaded)
        available_tools: Tools available for this client
        cliente_id: Client ID for prompt template lookup
        context_service: For loading additional sections if needed
        node_name: Name of the node (determines required sections)
    """
    from vizu_agent_framework.context_requirements import get_required_sections

    nome_empresa = safe_context.nome_empresa if safe_context else "Vizu"

    # Build tools description
    tools_description = build_tools_description(available_tools, ToolRegistry)

    # Format business hours
    horario_formatado = format_horario(
        safe_context.horario_funcionamento if safe_context else None
    )

    # Context 2.0: Get compiled context for required sections
    if safe_context and safe_context.loaded_sections:
        required_sections = get_required_sections(node_name)
        client_context_text = safe_context.get_compiled_context(required_sections)
    else:
        # Fallback to legacy prompt_base
        client_context_text = safe_context.prompt_base if safe_context else ""

    variables = {
        "nome_empresa": nome_empresa,
        "prompt_personalizado": client_context_text,
        "horario_formatado": horario_formatado,
        "tools_description": tools_description,
    }

    # Use unified prompt building
    return await build_prompt(
        name="atendente/system/v3",
        variables=variables,
        cliente_id=cliente_id,
        context_service=context_service,
    )
```

### Phase 6: Admin API (Week 3)

#### 6.1 Context Management Endpoints

**File:** `services/atendente_core/src/atendente_core/api/context.py` (new)

```python
"""
Context Management API - CRUD for client context sections.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from vizu_auth import verify_admin_token
from vizu_context_service import ContextService
from vizu_models.enums import ContextSection
from vizu_models.context_schemas import SECTION_SCHEMAS

from ..dependencies import get_context_service

router = APIRouter(prefix="/context", tags=["context"])


class SectionUpsertRequest(BaseModel):
    """Request body for upserting a section."""
    content: dict
    updated_by: str | None = None


class SectionResponse(BaseModel):
    """Response for section operations."""
    client_id: str
    section_type: str
    content: dict
    version: int
    last_updated_at: str | None


@router.get("/{client_id}/sections")
async def list_sections(
    client_id: UUID,
    context_service: ContextService = Depends(get_context_service),
    _: dict = Depends(verify_admin_token),
) -> dict[str, dict]:
    """List all context sections for a client."""
    sections = await context_service.get_context_sections(client_id)
    return {s.value: content for s, content in sections.items()}


@router.get("/{client_id}/sections/{section_type}")
async def get_section(
    client_id: UUID,
    section_type: ContextSection,
    context_service: ContextService = Depends(get_context_service),
    _: dict = Depends(verify_admin_token),
) -> dict:
    """Get a specific context section."""
    sections = await context_service.get_context_sections(
        client_id,
        sections=[section_type]
    )

    if section_type not in sections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section {section_type.value} not found for client"
        )

    return sections[section_type]


@router.put("/{client_id}/sections/{section_type}")
async def upsert_section(
    client_id: UUID,
    section_type: ContextSection,
    request: SectionUpsertRequest,
    context_service: ContextService = Depends(get_context_service),
    admin: dict = Depends(verify_admin_token),
) -> SectionResponse:
    """Create or update a context section."""
    # Validate content against schema
    schema_class = SECTION_SCHEMAS.get(section_type.value)
    if schema_class:
        try:
            schema_class.model_validate(request.content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid content for {section_type.value}: {str(e)}"
            )

    result = await context_service.upsert_context_section(
        client_id=client_id,
        section_type=section_type,
        content=request.content,
        updated_by=request.updated_by or admin.get("email", "admin"),
    )

    return SectionResponse(
        client_id=str(client_id),
        section_type=section_type.value,
        content=result.get("content", request.content),
        version=result.get("version", 1),
        last_updated_at=result.get("last_updated_at"),
    )


@router.delete("/{client_id}/sections/{section_type}")
async def delete_section(
    client_id: UUID,
    section_type: ContextSection,
    context_service: ContextService = Depends(get_context_service),
    _: dict = Depends(verify_admin_token),
) -> dict:
    """Deactivate a context section (soft delete)."""
    # Implementation would mark is_active=false
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Section deletion not yet implemented"
    )


@router.get("/{client_id}/compiled")
async def get_compiled_context(
    client_id: UUID,
    sections: list[ContextSection] | None = None,
    context_service: ContextService = Depends(get_context_service),
    _: dict = Depends(verify_admin_token),
) -> dict:
    """
    Get the compiled context string as it would be injected into prompts.

    Useful for debugging and previewing how context will appear to the LLM.
    """
    internal_ctx = await context_service.get_client_context_with_sections(
        client_id,
        sections=sections
    )

    compiled = internal_ctx.safe_context.get_compiled_context(sections)

    return {
        "client_id": str(client_id),
        "nome_empresa": internal_ctx.safe_context.nome_empresa,
        "tier": internal_ctx.safe_context.tier.value,
        "loaded_sections": [s.value for s in internal_ctx.safe_context.loaded_sections],
        "compiled_context": compiled,
    }


@router.get("/schemas")
async def list_schemas(
    _: dict = Depends(verify_admin_token),
) -> dict:
    """Get JSON schemas for all section types."""
    schemas = {}
    for section_name, schema_class in SECTION_SCHEMAS.items():
        schemas[section_name] = schema_class.model_json_schema()
    return schemas
```

---

## Migration Checklist

### Database (Supabase)

- [ ] Create `context_section_type` ENUM
- [ ] Create `client_context_sections` table
- [ ] Add RLS policies
- [ ] Create version trigger
- [ ] Add `tier_enum` column to `clientes_vizu`
- [ ] Migrate existing tier data
- [ ] Create indexes

### vizu_models

- [ ] Add `enums.py` with `ClientTier`, `ContextSection`
- [ ] Add `client_context_section.py` model
- [ ] Add `context_schemas.py` with section schemas
- [ ] Update `safe_client_context.py` with modular structure
- [ ] Update `__init__.py` exports
- [ ] Run `poetry lock`

### vizu_context_service

- [ ] Add `get_context_sections()` method
- [ ] Add `get_client_context_with_sections()` method
- [ ] Add `upsert_context_section()` method
- [ ] Add section cache management
- [ ] Update tests

### vizu_agent_framework

- [ ] Add `context_requirements.py`
- [ ] Update node functions to use selective injection
- [ ] Update `AgentState` if needed

### atendente_core

- [ ] Add context management API router
- [ ] Update `build_dynamic_system_prompt()`
- [ ] Update service layer to load sections

### Testing

- [ ] Unit tests for new models
- [ ] Integration tests for context loading
- [ ] E2E test with populated sections

---

## Data Population Guide

### Minimum Viable Context

For a client to have meaningful AI responses, populate at least:

1. **COMPANY_PROFILE** - Who they are
2. **BRAND_VOICE** - How to communicate
3. **CURRENT_MOMENT** - What's happening now

### Example: Complete Client Setup

```json
// COMPANY_PROFILE
{
  "legal_name": "Polen Soluções Ambientais Ltda.",
  "trading_name": "Polen",
  "business_archetype": "B2B Environmental Compliance",
  "mission": "Transformar a gestão de resíduos em vantagem competitiva",
  "vision": "Ser a plataforma de economia circular do Brasil",
  "core_values": ["Transparência Radical", "Impacto Mensurável", "Parceria de Longo Prazo"],
  "industry": "Environmental Services / GreenTech",
  "employee_count_range": "11-50"
}

// BRAND_VOICE
{
  "tone": "profissional, técnico mas acessível, parceiro estratégico",
  "personality_traits": ["confiável", "inovador", "orientado a dados"],
  "language": "pt-BR",
  "formality_level": "semi-formal",
  "key_phrases_to_use": [
    "economia circular",
    "rastreabilidade end-to-end",
    "compliance ambiental",
    "impacto mensurável"
  ],
  "phrases_to_avoid": [
    "100% sustentável",
    "eco-friendly (sem contexto)",
    "verde (como adjetivo vago)",
    "salvar o planeta"
  ],
  "communication_guidelines": "Sempre cite dados específicos quando disponíveis. Evite promessas vagas. Use linguagem que demonstre expertise técnica sem ser inacessível."
}

// CURRENT_MOMENT
{
  "stage": "growth",
  "current_priorities": [
    "Fechar 3 novos clientes enterprise até março",
    "Lançar dashboard de métricas ESG",
    "Reduzir churn em 20%"
  ],
  "current_challenges": [
    "Ciclo de vendas longo (60+ dias)",
    "Competição de consultorias tradicionais",
    "Integração com ERPs legados"
  ],
  "recent_wins": [
    "Contrato com Grupo Pão de Açúcar fechado",
    "Certificação ISO 14001 obtida",
    "NPS de 72 (acima da meta de 65)"
  ],
  "key_metrics": {
    "mrr": "crescimento de 15% MoM",
    "churn": "4.2% (meta: <5%)",
    "nps": 72
  },
  "week_of": "2024-W04"
}

// POLICIES
{
  "communication_rules": [
    "Sempre citar leis específicas (PNRS, CONAMA)",
    "Não fazer promessas de taxas de reciclagem sem dados",
    "Encaminhar questões jurídicas para compliance@polen.com"
  ],
  "operational_limits": [
    "Descontos > 15% requerem aprovação do comercial",
    "Prazos de implementação mínimos: 30 dias"
  ],
  "approval_requirements": {
    "autonomous": ["Responder dúvidas técnicas", "Agendar demos", "Enviar materiais"],
    "requires_approval": ["Propor descontos", "Alterar escopo", "Comprometer prazos"]
  },
  "red_flags": [
    "Cliente quer apenas certificado sem rastreabilidade real",
    "Pressão por greenwashing",
    "Solicitação de dados de outros clientes"
  ]
}
```

---

## Timeline Summary

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | Database + Models | Migration SQL, Enums, Section model |
| 2 | Context Service | Section loading, caching, SafeClientContext v2 |
| 3 | Agent Integration | Selective injection, Admin API |
| 4 | Testing + Docs | Full test coverage, User guide |

---

## Test Client: Polen (e0e9c949-18fe-4d9a-9295-d5dfb2cc9723)

Complete test data for Polen Soluções Ambientais.

### Status: ✅ DATA APPLIED

The Polen test client has been populated with all Context 2.0 sections via UPDATE statement on the `clientes_vizu` table.

**Verification query:**
```sql
SELECT
  client_id,
  nome_empresa,
  cpf_cnpj,
  tier,
  company_profile IS NOT NULL AS has_company_profile,
  brand_voice IS NOT NULL AS has_brand_voice,
  product_catalog IS NOT NULL AS has_product_catalog,
  target_audience IS NOT NULL AS has_target_audience,
  market_context IS NOT NULL AS has_market_context,
  current_moment IS NOT NULL AS has_current_moment,
  team_structure IS NOT NULL AS has_team_structure,
  policies IS NOT NULL AS has_policies,
  available_tools IS NOT NULL AS has_available_tools
FROM clientes_vizu
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
```

### Section Data Reference (JSON)

Below are the section contents for reference. These have been applied to the database.

#### COMPANY_PROFILE
```json
{
  "legal_name": "Polen Soluções Ambientais Ltda.",
  "trading_name": "Polen",
  "tagline": "Estruturamos a cadeia de reciclagem do Brasil",
  "business_archetype": "B2B Environmental Compliance & Circular Economy Enabler",
  "industry": "Waste Management/Recycling, Environmental Services, ESG Compliance",
  "mission": "Neutralizar a externalidade ambiental das embalagens no Brasil, estruturando cadeias de reciclagem eficientes e rastreáveis.",
  "vision": "Ser a plataforma que conecta todas as empresas brasileiras à economia circular, transformando obrigações legais em valor competitivo.",
  "core_values": [
    "Transparência Radical: Rastreabilidade total da cadeia",
    "Impacto Mensurável: Todo kg de resíduo tem história",
    "Parceria Estratégica: Não somos fornecedores, somos extensão do time ESG",
    "Inovação Pragmática: Soluções simples para problemas complexos"
  ]
}
```

#### BRAND_VOICE
  'brand_voice',
  '{
    "tone": "Profissional, técnico mas acessível; autoridade sem arrogância",
    "personality_traits": ["Confiável", "Inovador", "Parceiro", "Transparente", "Impactante"],
    "language": "pt-BR",
    "formality_level": "formal",
    "key_phrases_to_use": [
      "economia circular",
      "rastreabilidade",
      "compliance",
      "cadeia estruturada",
      "neutralização de externalidades"
    ],
    "phrases_to_avoid": [
      "sustentável (sem contexto específico)",
      "verde (como adjetivo vago)",
      "eco-friendly (sem métricas)",
      "100% sustentável"
    ],
    "preferred_terms": [
      "economia circular",
      "rastreabilidade end-to-end",
      "compliance PNRS",
      "impacto mensurável"
    ],
    "communication_guidelines": "Português brasileiro formal para clientes; técnico para relatórios. Sempre cite dados específicos quando disponíveis. Evite jargão ambiental vazio."
  }'::jsonb,
  'admin'
);

-- PRODUCT_CATALOG
INSERT INTO client_context_sections (client_id, section_type, content, updated_by)
VALUES (
  'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
  'product_catalog',
  '{
    "flagship_offering": "Neutralização de Externalidade de Embalagens",
    "services": [
      {
        "name": "Diagnóstico de Cadeia",
        "description": "Mapeamento completo do fluxo de embalagens",
        "category": "Consultoria"
      },
      {
        "name": "Estruturação Logística",
        "description": "Conexão com cooperativas parceiras certificadas",
        "category": "Operações"
      },
      {
        "name": "Rastreabilidade Digital",
        "description": "Plataforma com blockchain para tracking de resíduos",
        "category": "Tecnologia"
      },
      {
        "name": "Certificação e Compliance",
        "description": "Documentação completa para PNRS",
        "category": "Compliance"
      },
      {
        "name": "Engajamento do Consumidor",
        "description": "Códigos QR em embalagens com storytelling do ciclo",
        "category": "Marketing"
      }
    ],
    "pricing_tiers": [
      {
        "name": "Plano Básico",
        "description": "Até 10 ton/mês",
        "pricing_model": "per-unit"
      },
      {
        "name": "Plano Growth",
        "description": "10-100 ton/mês com relatórios mensais",
        "pricing_model": "per-unit"
      },
      {
        "name": "Plano Enterprise",
        "description": "100+ ton/mês - Consultoria personalizada + white label",
        "pricing_model": "custom"
      }
    ]
  }'::jsonb,
  'admin'
);

-- TARGET_AUDIENCE
INSERT INTO client_context_sections (client_id, section_type, content, updated_by)
VALUES (
  'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
  'target_audience',
  '{
    "primary_audience": "Empresas com pressão regulatória PNRS e compromissos ESG públicos",
    "ideal_customer_profile": "Empresas com faturamento > R$50M/ano, embalagens complexas (multimaterial), presença nacional",
    "industries_served": ["Alimentos & Bebidas", "Cosméticos", "Farmacêutico", "Varejo"],
    "company_size_target": "Faturamento > R$50M/ano",
    "buyer_personas": [
      {
        "role": "Diretor de Sustentabilidade",
        "responsibilities": "Estratégia ESG e metas de sustentabilidade",
        "pain_points": ["Pressão de investidores", "Metas ESG ambiciosas", "Falta de dados confiáveis"],
        "goals": ["Compliance PNRS", "Relatórios ESG robustos", "Redução de risco reputacional"]
      },
      {
        "role": "Jurídico Compliance",
        "responsibilities": "Garantir conformidade legal",
        "pain_points": ["Complexidade regulatória", "Documentação fragmentada"],
        "goals": ["Zero multas", "Documentação completa", "Auditabilidade"]
      },
      {
        "role": "Marketing (Branding Verde)",
        "responsibilities": "Comunicação de sustentabilidade",
        "pain_points": ["Acusações de greenwashing", "Falta de histórias reais"],
        "goals": ["Storytelling autêntico", "Diferenciação de marca", "Engajamento do consumidor"]
      }
    ],
    "common_pain_points": [
      "Pressão regulatória PNRS",
      "Compromissos ESG públicos difíceis de cumprir",
      "Embalagens complexas (multimaterial)",
      "Falta de rastreabilidade na cadeia"
    ]
  }'::jsonb,
  'admin'
);

-- MARKET_CONTEXT
INSERT INTO client_context_sections (client_id, section_type, content, updated_by)
VALUES (
  'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
  'market_context',
  '{
    "key_competitors": [
      {
        "name": "Empresa A",
        "positioning": "Foco em logística reversa básica",
        "strengths": ["Preço mais baixo", "Rede ampla"],
        "weaknesses": ["Menos tecnologia", "Sem rastreabilidade blockchain"]
      },
      {
        "name": "Empresa B",
        "positioning": "Consultoria ESG ampla",
        "strengths": ["Marca conhecida", "Serviços amplos"],
        "weaknesses": ["Menos especializado em embalagens", "Genérico"]
      }
    ],
    "differentiators": [
      "Tecnologia de rastreabilidade (blockchain platform)",
      "Foco exclusivo em embalagens",
      "Modelo de engajamento do consumidor (código QR com storytelling)",
      "Rede de cooperativas certificadas"
    ],
    "market_position": "Specialist leader em compliance de embalagens",
    "regulatory_environment": "PNRS (Lei 12.305/2010) - Logística Reversa obrigatória para embalagens. Setores têm acordos setoriais com metas específicas. Riscos: multas, dano reputacional, responsabilidade pós-consumo.",
    "compliance_requirements": [
      "PNRS Art. 33 - Logística Reversa",
      "Acordos setoriais por categoria",
      "Relatórios anuais de gestão de resíduos"
    ],
    "market_trends": [
      "ESG como critério de investimento",
      "Consumidor exigindo transparência",
      "Tributação verde em discussão",
      "Marca circular como diferencial competitivo"
    ]
  }'::jsonb,
  'admin'
);

-- CURRENT_MOMENT
INSERT INTO client_context_sections (client_id, section_type, content, updated_by)
VALUES (
  'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
  'current_moment',
  '{
    "stage": "growth",
    "period": "Q4 2024 - Q1 2025",
    "current_priorities": [
      "Fechar 3 contratos Enterprise até março/2025",
      "Lançar dashboard white-label para clientes B2B2C",
      "Expandir rede de cooperativas para Norte/Nordeste"
    ],
    "current_challenges": [
      "Capacitação de cooperativas em regiões remotas",
      "Custo logístico no Centro-Oeste",
      "Educação do mercado sobre PNRS real vs. greenwashing",
      "Integração com ERPs dos clientes (diversos sistemas)"
    ],
    "recent_wins": [
      "Certificação ISO 14001 obtida",
      "Parceria com associação de supermercados",
      "Case study com cliente de cosméticos mostrou ROI 140% em brand value",
      "Selecionada para programa de aceleração do BID"
    ],
    "key_metrics": {
      "note": "Métricas detalhadas via MetricService"
    },
    "active_campaigns": [
      "Série A fundraising em andamento"
    ],
    "upcoming_events": [],
    "last_updated": "2024-01-29"
  }'::jsonb,
  'admin'
);

-- TEAM_STRUCTURE
INSERT INTO client_context_sections (client_id, section_type, content, updated_by)
VALUES (
  'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
  'team_structure',
  '{
    "key_contacts": [
      {"role": "CEO", "name": "Ana Silva", "responsibility": "Estratégia e fundraising"},
      {"role": "COO", "name": "Carlos Mendes", "responsibility": "Operações e cooperativas"},
      {"role": "CTO", "name": "João Santos", "responsibility": "Plataforma e blockchain"},
      {"role": "Head Comercial", "name": "Mariana Lima", "responsibility": "Vendas B2B"}
    ],
    "main_contact": "Rafael Costa (Customer Success)",
    "escalation_path": [
      "Customer Success (Rafael) → Head Comercial (Mariana) → CEO (Ana)"
    ],
    "communication_channels": {
      "urgent": "Slack",
      "formal": "Email"
    },
    "headquarters": "São Paulo (Vila Olímpia)",
    "operational_locations": ["SP", "RJ", "MG", "PR"],
    "business_hours": "Seg-Sex 8h-18h (BRT)"
  }'::jsonb,
  'admin'
);

-- POLICIES
INSERT INTO client_context_sections (client_id, section_type, content, updated_by)
VALUES (
  'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
  'policies',
  '{
    "communication_rules": [
      "Assertividade Técnica: Sempre citar leis específicas (PNRS Art. 33, CONAMA)",
      "Evitar Greenwashing: Nunca dizer 100% sustentável - usar neutralização de externalidade",
      "Transparência: Se não souber dados exatos, dizer preciso verificar na plataforma",
      "Dados primeiro: Sempre que possível, cite números e métricas específicas"
    ],
    "tone_with_partners": "Respeitoso e colaborativo - cooperativas são parceiras, não fornecedoras",
    "operational_limits": [
      "Descontos > 15% requerem aprovação do Head Comercial",
      "Prazos de implementação mínimos: 30 dias",
      "Não prometer taxas de reciclagem sem dados reais da plataforma"
    ],
    "approval_requirements": {
      "autonomous": [
        "Responder dúvidas técnicas sobre PNRS",
        "Agendar demos e reuniões",
        "Enviar materiais de marketing aprovados",
        "Consultar dados agregados da plataforma"
      ],
      "requires_approval": [
        "Propor descontos acima de 10%",
        "Alterar escopo de projeto",
        "Comprometer prazos específicos",
        "Compartilhar dados de outros clientes"
      ]
    },
    "red_flags": [
      "Cliente quer apenas certificado sem rastreabilidade real",
      "Pressão para fazer afirmações de greenwashing",
      "Solicitação de dados de outros clientes",
      "Pedidos para burlar compliance"
    ],
    "compliance_notes": "Toda comunicação deve ser auditável. Gravações de reunião disponíveis mediante solicitação.",
    "data_handling_rules": [
      "Dados de clientes são confidenciais",
      "Métricas agregadas podem ser compartilhadas",
      "Dados individuais apenas com autorização"
    ]
  }'::jsonb,
  'admin'
);

-- AVAILABLE_TOOLS
INSERT INTO client_context_sections (client_id, section_type, content, updated_by)
VALUES (
  'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',
  'available_tools',
  '{
    "tier": "ENTERPRISE",
    "enabled_tool_names": ["executar_rag_cliente", "executar_sql_agent"],
    "tool_descriptions": {
      "executar_rag_cliente": "Busca semântica na base de conhecimento da Polen",
      "executar_sql_agent": "Consulta dados estruturados de métricas e operações"
    },
    "autonomous_actions": [
      "Consultar base de conhecimento",
      "Executar queries de dados agregados",
      "Gerar relatórios padrão"
    ],
    "restricted_actions": [
      "Modificar dados",
      "Acessar dados de outros clientes",
      "Aprovar transações"
    ],
    "usage_limits": {
      "queries_per_hour": 100,
      "max_result_rows": 1000
    },
    "default_system_prompt": "Você é um analista de dados especializado da Polen. Atue como uma extensão da equipe, sempre provendo os dados necessários pedidos. Use dados concretos da plataforma sempre, consulte sua base de dados."
  }'::jsonb,
  'admin'
);
```

---

## Next Steps

1. **Review this plan** - Confirm scope and approach
2. **Apply database migration** - Create tables in Supabase
3. **Implement models** - ✅ DONE (vizu_models updated)
4. **Populate test client** - Run SQL above for Polen
5. **Test end-to-end** - Verify AI responses improve

---

## Questions to Resolve

1. **Legacy `prompt_base`** - Keep as fallback forever or deprecate after migration?
2. **Section versioning** - Do we need full history or just current + previous?
3. **Admin UI** - Build dedicated UI or use Supabase dashboard for now?
4. **Auto-generation** - Should we use AI to help populate initial sections from existing data?
