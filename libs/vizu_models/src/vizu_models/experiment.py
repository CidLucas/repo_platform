# libs/vizu_models/src/vizu_models/experiment.py
"""
Experiment Models for Dataset Generation Pipeline.

This module defines the data models for running experiments against the
atendente API, collecting results, routing to HITL, and generating
training datasets.

Flow:
1. ExperimentManifest defines what to test (cases, clients, prompts)
2. ExperimentRun tracks execution of a manifest
3. ExperimentCase represents individual test cases with results
4. Results are classified and routed to HITL or directly to dataset
5. HITL-reviewed items become golden training samples
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from sqlmodel import JSON, Column, Relationship, SQLModel
from sqlmodel import Field as SQLField

# ============================================================================
# ENUMS
# ============================================================================


class ExperimentStatus(Enum):
    """Status of an experiment run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CaseOutcome(Enum):
    """Outcome classification of a test case."""

    SUCCESS = "success"  # Response matched expectations
    FAILURE = "failure"  # Response did not match expectations
    ERROR = "error"  # Execution error (API failed, timeout, etc.)
    NEEDS_REVIEW = "needs_review"  # Routed to HITL for human review
    REVIEWED = "reviewed"  # HITL review completed
    SKIPPED = "skipped"  # Case was skipped


class ClassificationResult(Enum):
    """Auto-classification of response quality."""

    HIGH_CONFIDENCE = "high_confidence"  # Good response, save directly
    MEDIUM_CONFIDENCE = "medium_confidence"  # Uncertain, route to HITL
    LOW_CONFIDENCE = "low_confidence"  # Poor response, route to HITL
    TOOL_USED = "tool_used"  # Tool was called (may need review)
    ELICITATION = "elicitation"  # Elicitation was triggered
    ERROR = "error"  # Error occurred


# ============================================================================
# PYDANTIC MODELS (Manifests & Config)
# ============================================================================


class TestCaseDefinition(BaseModel):
    """Definition of a single test case in the manifest."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    message: str = Field(..., description="Input message to send")
    cliente_id: str | None = Field(
        None, description="Specific client ID (overrides manifest default)"
    )
    expected_tool: str | None = Field(None, description="Expected tool to be called")
    expected_contains: list[str] | None = Field(
        None, description="Substrings expected in response"
    )
    expected_not_contains: list[str] | None = Field(
        None, description="Substrings NOT expected"
    )
    tags: list[str] | None = Field(
        default_factory=list, description="Tags for filtering"
    )
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class ClientVariant(BaseModel):
    """A client configuration variant for the experiment."""

    cliente_id: str = Field(..., description="UUID of the ClienteVizu")
    name: str = Field(..., description="Human-readable name for this variant")
    description: str | None = None
    enabled_tools: list[str] | None = Field(
        None, description="Tools to test (None = all enabled)"
    )


class HitlRoutingConfig(BaseModel):
    """Configuration for HITL routing during experiment."""

    enabled: bool = Field(True, description="Enable HITL routing")
    confidence_threshold: float = Field(
        0.7, description="Below this confidence -> HITL"
    )
    sample_rate: float = Field(0.1, description="Random sample rate for HITL")
    always_review_tools: list[str] = Field(
        default_factory=lambda: ["executar_sql_agent"],
        description="Always review when these tools are called",
    )
    always_review_first_n: int = Field(
        3, description="Always review first N cases per client"
    )


class LangfuseConfig(BaseModel):
    """Configuration for Langfuse integration."""

    enabled: bool = Field(True)
    session_prefix: str = Field("exp-", description="Prefix for session IDs")
    tags: list[str] = Field(default_factory=lambda: ["experiment"])
    create_dataset: bool = Field(True, description="Create dataset from results")
    dataset_name: str | None = Field(
        None, description="Dataset name (auto-generated if None)"
    )


class ExperimentManifest(BaseModel):
    """
    Complete experiment definition.

    This is the input document that defines what experiment to run.
    Can be stored as YAML/JSON and versioned.
    """

    name: str = Field(..., description="Experiment name")
    version: str = Field("1.0.0", description="Manifest version")
    description: str | None = None

    # Target API
    api_url: str = Field("http://localhost:8003", description="Atendente API URL")

    # Client variants to test
    clients: list[ClientVariant] = Field(
        ..., description="Client configurations to test"
    )

    # Test cases
    cases: list[TestCaseDefinition] = Field(..., description="Test cases to run")

    # Optional: Cases per client (different questions per client)
    client_specific_cases: dict[str, list[TestCaseDefinition]] | None = Field(
        None, description="Client-specific test cases (keyed by cliente_id)"
    )

    # Execution config
    parallel_requests: int = Field(5, description="Max parallel requests")
    timeout_seconds: int = Field(60, description="Request timeout")
    retry_count: int = Field(2, description="Retries on failure")

    # HITL config
    hitl: HitlRoutingConfig = Field(default_factory=HitlRoutingConfig)

    # Langfuse config
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)

    # Metadata
    created_by: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: list[str] = Field(default_factory=list)


# ============================================================================
# SQLMODEL TABLES (Persistence)
# ============================================================================


class ExperimentRun(SQLModel, table=True):
    """
    Record of a single experiment execution.

    Links to the manifest used and tracks overall status.
    """

    __tablename__ = "experiment_run"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)

    # Manifest info
    manifest_name: str = SQLField(index=True)
    manifest_version: str
    manifest_json: dict[str, Any] = SQLField(sa_column=Column(JSON))

    # Execution info
    status: str = SQLField(default=ExperimentStatus.PENDING.value)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Stats
    total_cases: int = SQLField(default=0)
    completed_cases: int = SQLField(default=0)
    success_cases: int = SQLField(default=0)
    failure_cases: int = SQLField(default=0)
    error_cases: int = SQLField(default=0)
    hitl_routed_cases: int = SQLField(default=0)

    # Langfuse link
    langfuse_session_id: str | None = None
    langfuse_dataset_id: str | None = None

    # Metadata
    created_by: str | None = None
    notes: str | None = None

    # Timestamps
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    updated_at: datetime = SQLField(default_factory=datetime.utcnow)

    # Relationships
    cases: list["ExperimentCase"] = Relationship(back_populates="run")


class ExperimentCase(SQLModel, table=True):
    """
    Individual test case result within an experiment run.

    Links to HITL review if routed for human review.
    """

    __tablename__ = "experiment_case"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)

    # Parent run
    run_id: uuid.UUID = SQLField(foreign_key="experiment_run.id", index=True)
    run: ExperimentRun | None = Relationship(back_populates="cases")

    # Test case info
    case_id: str = SQLField(index=True)  # From manifest
    cliente_id: uuid.UUID = SQLField(index=True)
    cliente_name: str  # Denormalized for easy querying

    # Input
    input_message: str
    expected_tool: str | None = None
    expected_contains: list[str] | None = SQLField(sa_column=Column(JSON))

    # Output
    actual_response: str | None = None
    actual_tool_called: str | None = None
    tools_called: list[str] | None = SQLField(sa_column=Column(JSON))
    model_used: str | None = None

    # Classification
    outcome: str = SQLField(default=CaseOutcome.NEEDS_REVIEW.value)
    classification: str | None = None
    confidence_score: float | None = None

    # Assertions
    tool_assertion_passed: bool | None = None
    contains_assertion_passed: bool | None = None

    # HITL link
    hitl_review_id: uuid.UUID | None = SQLField(
        foreign_key="hitl_review.id", nullable=True
    )
    hitl_routed_reason: str | None = None

    # Langfuse link
    langfuse_trace_id: str | None = None

    # Timing
    request_duration_ms: int | None = None

    # Metadata
    error_message: str | None = None
    raw_response: dict[str, Any] | None = SQLField(sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    updated_at: datetime = SQLField(default_factory=datetime.utcnow)


# ============================================================================
# HELPER MODELS
# ============================================================================


class ExperimentRunSummary(BaseModel):
    """Summary of an experiment run for display."""

    id: str
    name: str
    version: str
    status: ExperimentStatus
    started_at: datetime | None
    completed_at: datetime | None
    total_cases: int
    success_rate: float
    hitl_rate: float
    langfuse_url: str | None


class ExperimentProgress(BaseModel):
    """Real-time progress of a running experiment."""

    run_id: str
    status: ExperimentStatus
    total: int
    completed: int
    success: int
    failures: int
    errors: int
    hitl_routed: int
    current_client: str | None
    elapsed_seconds: float
    estimated_remaining_seconds: float | None


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    # Enums
    "ExperimentStatus",
    "CaseOutcome",
    "ClassificationResult",
    # Pydantic models
    "TestCaseDefinition",
    "ClientVariant",
    "HitlRoutingConfig",
    "LangfuseConfig",
    "ExperimentManifest",
    "ExperimentRunSummary",
    "ExperimentProgress",
    # SQLModel tables
    "ExperimentRun",
    "ExperimentCase",
]
