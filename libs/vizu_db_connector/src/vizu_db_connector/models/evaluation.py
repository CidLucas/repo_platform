import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import relationship

# Importa a Base declarativa da própria biblioteca
from .base import Base

class EvaluationRun(Base):
    """
    Modelo SQLAlchemy para uma execução da suíte de avaliação.
    """
    __tablename__ = 'evaluation_runs'

    run_id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp_start = Column(DateTime, nullable=False)
    timestamp_end = Column(DateTime, nullable=True)
    dataset_name = Column(String, nullable=False)
    assistant_version = Column(String, nullable=False)
    status = Column(String, nullable=False) # Ex: RUNNING, COMPLETED, FAILED

    # Relacionamento
    test_results = relationship("TestResult", back_populates="evaluation_run")


class TestResult(Base):
    """
    Modelo SQLAlchemy para o resultado de um único caso de teste.
    """
    __tablename__ = 'test_results'

    result_id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(pgUUID(as_uuid=True), ForeignKey('evaluation_runs.run_id'), nullable=False)
    clientevizu_id = Column(pgUUID(as_uuid=True), ForeignKey('cliente_vizu.id'), nullable=False)
    input_message = Column(Text, nullable=False)
    actual_output = Column(Text, nullable=True) # A resposta do assistente

    # Relacionamentos
    evaluation_run = relationship("EvaluationRun", back_populates="test_results")
    cliente_vizu = relationship("ClienteVizu")