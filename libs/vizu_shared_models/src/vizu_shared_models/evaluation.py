import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# --- EvaluationRun ---

class EvaluationRunBase(BaseModel):
    """Modelo Pydantic base - campos que o usuário pode inserir."""
    dataset_name: str
    assistant_version: str
    status: str

class EvaluationRunRead(EvaluationRunBase):
    """Modelo Pydantic para ler dados do banco."""
    run_id: uuid.UUID
    timestamp_start: datetime
    timestamp_end: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# --- TestResult ---

class TestResultBase(BaseModel):
    """Modelo Pydantic base para um resultado de teste."""
    clientevizu_id: uuid.UUID
    input_message: str
    actual_output: str | None = None

class TestResultRead(TestResultBase):
    """Modelo Pydantic para ler o resultado do teste do banco."""
    result_id: uuid.UUID
    run_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)