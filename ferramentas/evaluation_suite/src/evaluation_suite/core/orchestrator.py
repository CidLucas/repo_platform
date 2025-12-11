import asyncio
import uuid
from datetime import datetime

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

# Importamos os modelos SQLModel de vizu_models
from vizu_models import (
    CaseOutcome,
    Conversa,
    ExperimentCase,
    ExperimentRun,
    ExperimentStatus,
)

# Nossas bibliotecas e modelos reais
# NÃO importamos mais nada de crud.py ou operations.py
from ..clients.api_client import APIClient


class EvaluationOrchestrator:

    def __init__(self, db_session: Session, assistant_client: APIClient):
        self.db = db_session
        self.assistant_client = assistant_client
        logger.info("EvaluationOrchestrator (async) inicializado.")

    def _load_dataset_from_csv(self, dataset_path: str) -> list[dict]:
        try:
            logger.info(f"Carregando dataset do arquivo: {dataset_path}")
            df = pd.read_csv(dataset_path)
            if 'clientevizu_id' not in df.columns or 'message' not in df.columns:
                raise ValueError("O dataset CSV precisa ter as colunas 'clientevizu_id' and 'message'.")

            # Valida se o ID do cliente é um UUID válido
            try:
                df['clientevizu_id'] = df['clientevizu_id'].apply(lambda x: uuid.UUID(x))
            except ValueError as e:
                logger.error(f"Coluna 'clientevizu_id' contém IDs que não são UUIDs válidos. Erro: {e}")
                raise

            records = df.to_dict('records')
            logger.info(f"{len(records)} casos de teste carregados.")
            return records
        except FileNotFoundError:
            logger.error(f"Arquivo do dataset não encontrado em: {dataset_path}")
            raise
        except Exception as e:
            logger.error(f"Falha ao carregar ou processar o dataset CSV: {e}")
            raise

    def _collect_results_from_db(self, run_id: uuid.UUID, test_cases: list[dict], start_time: datetime):
        """
        Busca no banco de dados as conversas geradas durante a execução
        e as salva como ExperimentCase.
        """
        logger.info(f"Coletando resultados do banco de dados para o Run ID: {run_id}...")

        client_ids = list(set(case['clientevizu_id'] for case in test_cases))

        # CORREÇÃO: Usamos db.query() diretamente.
        conversas_criadas = self.db.query(Conversa).filter(
            Conversa.clientevizu_id.in_(client_ids),
            Conversa.timestamp_criacao >= start_time
        ).all()

        logger.info(f"{len(conversas_criadas)} conversas encontradas para esta execução.")

        novos_resultados = []
        for case in test_cases:
            found_response = "RESPOSTA NÃO ENCONTRADA NO DB"
            for conv in conversas_criadas:
                if conv.clientevizu_id == case['clientevizu_id'] and conv.mensagem == case['message']:
                    found_response = conv.resposta
                    break

            # Criamos o objeto ExperimentCase
            db_result = ExperimentCase(
                run_id=run_id,
                cliente_id=case['clientevizu_id'],
                input_message=case['message'],
                actual_response=found_response,
                outcome=CaseOutcome.SUCCESS.value if found_response != "RESPOSTA NÃO ENCONTRADA NO DB" else CaseOutcome.ERROR.value,
            )
            novos_resultados.append(db_result)

        # Adicionamos todos os novos resultados à sessão de uma vez
        if novos_resultados:
            self.db.add_all(novos_resultados)
            self.db.commit() # Commit dos resultados dos testes

        logger.success("Resultados da avaliação foram persistidos com sucesso na tabela experiment_case.")


    async def run_evaluation(self, dataset_path: str, assistant_version: str):
        """
        Ponto de entrada principal para executar uma avaliação completa.
        """
        start_time = datetime.utcnow()
        run_id = uuid.uuid4()

        experiment_run = None # Inicializa a variável
        try:
            # Criamos o objeto ExperimentRun
            experiment_run = ExperimentRun(
                id=run_id,
                manifest_name=dataset_path.split('/')[-1],
                manifest_json={"dataset_path": dataset_path, "assistant_version": assistant_version},
                status=ExperimentStatus.RUNNING.value,
                created_by=assistant_version,
            )
            # Adicionamos à sessão e fazemos o commit
            self.db.add(experiment_run)
            self.db.commit()
            self.db.refresh(experiment_run) # Atualiza o objeto com dados do DB (ex: defaults)

            logger.info(f"ExperimentRun criado com ID: {run_id}")

            test_cases = self._load_dataset_from_csv(dataset_path)

            logger.info(f"Disparando {len(test_cases)} mensagens para a API...")
            tasks = [ self.assistant_client.send_message(
                clientevizu_id=str(case['clientevizu_id']), message=case['message']
            ) for case in test_cases]
            await asyncio.gather(*tasks)
            logger.success("Todas as mensagens foram enviadas com sucesso.")

            logger.info("Aguardando para garantir a persistência dos dados...")
            await asyncio.sleep(5)

            self._collect_results_from_db(run_id, test_cases, start_time)

            # Atualizamos o objeto ExperimentRun
            experiment_run.status = ExperimentStatus.COMPLETED.value
            experiment_run.completed_at = datetime.utcnow()
            self.db.add(experiment_run)
            self.db.commit()

            logger.success(f"Avaliação (Run ID: {run_id}) concluída com sucesso.")

        except FileNotFoundError:
            logger.error(f"Execução falhou porque o dataset não foi encontrado: {dataset_path}.")
            if experiment_run:
                experiment_run.status = ExperimentStatus.FAILED.value
                experiment_run.completed_at = datetime.utcnow()
                self.db.add(experiment_run)
                self.db.commit()
            raise

        except Exception as e:
            logger.error(f"Erro crítico durante a execução (Run ID: {run_id}): {e}")
            if experiment_run:
                experiment_run.status = ExperimentStatus.FAILED.value
                experiment_run.completed_at = datetime.utcnow()
                self.db.add(experiment_run)
                self.db.commit()

        return str(run_id)
