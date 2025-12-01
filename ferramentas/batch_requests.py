"""
Script de Batch Requests para testar o Atendente.
Le um arquivo CSV com mensagens de teste e faz requests em serie,
registrando respostas, ferramentas usadas e metricas.

Busca automaticamente as API keys do banco de dados (Supabase ou local).

Uso:
    python batch_requests.py --csv mensagens_teste.csv --output resultados.csv
    python batch_requests.py --csv mensagens_teste.csv --db-url <URL> --verbose
    python batch_requests.py --csv mensagens_teste.csv --supabase  # usa Supabase prod

Formato do CSV de entrada:
    cliente_nome,cliente_final_id,mensagem,categoria_teste
    "Studio J","user_123","Quero agendar um corte para sabado","agendamento"
    "Oficina Mendes","user_456","Meu carro ta pronto?","status"

Saida:
    - CSV com respostas, ferramentas usadas, tempo de resposta
    - Metricas agregadas no console
"""
import argparse
import csv
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

try:
    from sqlalchemy import create_engine, text
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

# Configuracoes padrao
DEFAULT_API_URL = "http://localhost:8003"
DOCKER_API_URL = "http://atendente_core:8000"  # Porta interna do container
DEFAULT_TIMEOUT = 60
DEFAULT_SLEEP_BETWEEN_REQUESTS = 1.5  # segundos entre requests

# DB URLs padrao
LOCAL_DB_URL = "postgresql://user:password@localhost:5433/vizu_db"


def detect_api_url() -> str:
    """Detecta se estamos rodando dentro do Docker ou no host."""
    import socket
    try:
        # Tenta resolver o hostname do container
        socket.gethostbyname("atendente_core")
        return DOCKER_API_URL
    except socket.gaierror:
        return DEFAULT_API_URL


@dataclass
class TestResult:
    """Resultado de um teste individual."""
    # Identificacao
    test_id: str
    timestamp: str

    # Input
    cliente_nome: str
    cliente_final_id: str
    mensagem: str
    categoria_teste: str

    # Output
    resposta: str = ""
    status_code: int = 0
    tempo_resposta_ms: int = 0

    # Analise
    ferramentas_usadas: List[str] = field(default_factory=list)
    usou_rag: bool = False
    usou_sql: bool = False
    usou_agendamento: bool = False
    erro: str = ""

    # Metadados
    thread_id: str = ""
    raw_response: Dict = field(default_factory=dict)


@dataclass
class BatchStats:
    """Estatisticas agregadas do batch."""
    total_requests: int = 0
    sucessos: int = 0
    erros: int = 0
    tempo_total_ms: int = 0
    tempo_medio_ms: float = 0

    # Uso de ferramentas
    requests_com_rag: int = 0
    requests_com_sql: int = 0
    requests_com_agendamento: int = 0

    # Por categoria
    por_categoria: Dict[str, Dict] = field(default_factory=dict)


def load_api_keys_from_db(db_url: str) -> Dict[str, str]:
    """Carrega mapeamento cliente_nome -> api_key do banco de dados."""
    if not HAS_SQLALCHEMY:
        raise ImportError("sqlalchemy nao encontrado. Instale com: pip install sqlalchemy psycopg2-binary")

    print(f"🔑 Carregando API keys do banco de dados...")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT nome_empresa, api_key FROM cliente_vizu WHERE api_key IS NOT NULL"))
        rows = result.fetchall()

    api_keys = {row[0]: row[1] for row in rows}
    print(f"   ✅ {len(api_keys)} clientes carregados: {list(api_keys.keys())}")
    return api_keys


class BatchRequester:
    """Executor de batch requests para o atendente."""

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        api_keys: Dict[str, str] = None,
        jwt_token: str = None,
        timeout: int = DEFAULT_TIMEOUT,
        verbose: bool = False,
        sleep_between: float = DEFAULT_SLEEP_BETWEEN_REQUESTS
    ):
        self.api_url = api_url.rstrip("/")
        self.api_keys = api_keys or {}  # cliente_nome -> api_key
        self.jwt_token = jwt_token
        self.timeout = timeout
        self.verbose = verbose
        self.sleep_between = sleep_between
        self.results: List[TestResult] = []
        self.stats = BatchStats()

    def _get_headers(self, cliente_nome: str) -> Dict[str, str]:
        """Gera headers para a request, usando a API key do cliente."""
        headers = {"Content-Type": "application/json"}

        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        elif cliente_nome in self.api_keys:
            headers["X-API-Key"] = self.api_keys[cliente_nome]
        else:
            self._log(f"⚠️ Nenhuma API key encontrada para '{cliente_nome}'", "warn")

        return headers

    def _log(self, msg: str, level: str = "info"):
        """Log com nivel."""
        if self.verbose or level == "error":
            prefix = {"info": "ℹ️", "success": "✅", "error": "❌", "warn": "⚠️"}.get(level, "")
            print(f"{prefix} {msg}")

    def _parse_response(self, response_data: Dict) -> tuple:
        """Extrai informacoes da resposta do atendente."""
        resposta = ""
        ferramentas = []
        usou_rag = False
        usou_sql = False
        usou_agendamento = False
        thread_id = ""

        # Formato esperado: {"response": "...", "thread_id": "...", "tools_used": [...]}
        if isinstance(response_data, dict):
            resposta = response_data.get("response", response_data.get("message", str(response_data)))
            thread_id = response_data.get("thread_id", "")

            # Analisa ferramentas usadas (se disponivel na resposta)
            tools = response_data.get("tools_used", [])
            if tools:
                ferramentas = tools
                usou_rag = any("rag" in t.lower() or "search" in t.lower() or "conhecimento" in t.lower() for t in tools)
                usou_sql = any("sql" in t.lower() or "query" in t.lower() for t in tools)
                usou_agendamento = any("agend" in t.lower() or "schedule" in t.lower() or "booking" in t.lower() for t in tools)

            # Heuristica: detecta uso de RAG pela resposta
            if any(kw in resposta.lower() for kw in ["base de conhecimento", "encontrei", "segundo", "de acordo"]):
                usou_rag = True
            if any(kw in resposta.lower() for kw in ["agendar", "agendamento", "horário", "disponível"]):
                usou_agendamento = True
        else:
            resposta = str(response_data)

        return resposta, ferramentas, usou_rag, usou_sql, usou_agendamento, thread_id

    def execute_request(
        self,
        cliente_nome: str,
        cliente_final_id: str,
        mensagem: str,
        categoria_teste: str = "",
        thread_id: str = None
    ) -> TestResult:
        """Executa uma request individual."""
        test_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        result = TestResult(
            test_id=test_id,
            timestamp=timestamp,
            cliente_nome=cliente_nome,
            cliente_final_id=cliente_final_id,
            mensagem=mensagem,
            categoria_teste=categoria_teste
        )

        # Monta payload
        # Gera um session_id unico para cada cliente_final
        session_id = thread_id or f"batch-{cliente_final_id}"

        payload = {
            "message": mensagem,
            "cliente_final_id": cliente_final_id,
            "session_id": session_id
        }

        # URL do endpoint
        endpoint = f"{self.api_url}/api/v1/chat"

        self._log(f"[{test_id}] {cliente_nome} <- \"{mensagem[:50]}...\"")

        try:
            start_time = time.time()

            response = requests.post(
                endpoint,
                json=payload,
                headers=self._get_headers(cliente_nome),
                timeout=self.timeout
            )

            elapsed_ms = int((time.time() - start_time) * 1000)
            result.tempo_resposta_ms = elapsed_ms
            result.status_code = response.status_code

            if response.status_code == 200:
                response_data = response.json()
                result.raw_response = response_data

                (
                    result.resposta,
                    result.ferramentas_usadas,
                    result.usou_rag,
                    result.usou_sql,
                    result.usou_agendamento,
                    result.thread_id
                ) = self._parse_response(response_data)

                self._log(f"[{test_id}] -> {result.resposta[:80]}... ({elapsed_ms}ms)", "success")

                if result.ferramentas_usadas:
                    self._log(f"[{test_id}] 🔧 Ferramentas: {result.ferramentas_usadas}")
            else:
                result.erro = f"HTTP {response.status_code}: {response.text[:200]}"
                self._log(f"[{test_id}] {result.erro}", "error")

        except requests.exceptions.Timeout:
            result.erro = f"Timeout apos {self.timeout}s"
            self._log(f"[{test_id}] {result.erro}", "error")
        except requests.exceptions.ConnectionError as e:
            result.erro = f"Erro de conexao: {str(e)[:100]}"
            self._log(f"[{test_id}] {result.erro}", "error")
        except Exception as e:
            result.erro = f"Erro: {str(e)[:100]}"
            self._log(f"[{test_id}] {result.erro}", "error")

        self.results.append(result)
        return result

    def run_from_csv(self, csv_path: str) -> List[TestResult]:
        """Executa batch a partir de arquivo CSV."""
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {csv_path}")

        print(f"\n{'='*60}")
        print(f"🚀 BATCH REQUEST - {csv_path.name}")
        print(f"{'='*60}")
        print(f"   API: {self.api_url}")
        print(f"   Auth: {'JWT' if self.jwt_token else f'API Keys ({len(self.api_keys)} clientes)' if self.api_keys else 'Nenhuma'}")
        print(f"   Sleep entre requests: {self.sleep_between}s")
        print(f"{'='*60}\n")

        # Le CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"📋 {len(rows)} mensagens para processar\n")

        # Processa cada linha
        for i, row in enumerate(rows, 1):
            print(f"\n[{i}/{len(rows)}] ", end="")

            self.execute_request(
                cliente_nome=row.get("cliente_nome", ""),
                cliente_final_id=row.get("cliente_final_id", f"test_user_{i}"),
                mensagem=row.get("mensagem", ""),
                categoria_teste=row.get("categoria_teste", "")
            )

            # Sleep configuravel entre requests
            if i < len(rows):
                time.sleep(self.sleep_between)

        self._compute_stats()
        return self.results

    def _compute_stats(self):
        """Calcula estatisticas agregadas."""
        self.stats = BatchStats()
        self.stats.total_requests = len(self.results)

        for r in self.results:
            if r.status_code == 200 and not r.erro:
                self.stats.sucessos += 1
            else:
                self.stats.erros += 1

            self.stats.tempo_total_ms += r.tempo_resposta_ms

            if r.usou_rag:
                self.stats.requests_com_rag += 1
            if r.usou_sql:
                self.stats.requests_com_sql += 1
            if r.usou_agendamento:
                self.stats.requests_com_agendamento += 1

            # Por categoria
            cat = r.categoria_teste or "sem_categoria"
            if cat not in self.stats.por_categoria:
                self.stats.por_categoria[cat] = {"total": 0, "sucesso": 0, "tempo_ms": 0}
            self.stats.por_categoria[cat]["total"] += 1
            if r.status_code == 200:
                self.stats.por_categoria[cat]["sucesso"] += 1
            self.stats.por_categoria[cat]["tempo_ms"] += r.tempo_resposta_ms

        if self.stats.total_requests > 0:
            self.stats.tempo_medio_ms = self.stats.tempo_total_ms / self.stats.total_requests

    def print_stats(self):
        """Imprime estatisticas no console."""
        s = self.stats

        print(f"\n{'='*60}")
        print("📊 ESTATISTICAS DO BATCH")
        print(f"{'='*60}")
        print(f"   Total de requests: {s.total_requests}")
        print(f"   Sucessos: {s.sucessos} ({100*s.sucessos/max(1,s.total_requests):.1f}%)")
        print(f"   Erros: {s.erros}")
        print(f"   Tempo medio: {s.tempo_medio_ms:.0f}ms")
        print(f"   Tempo total: {s.tempo_total_ms/1000:.1f}s")
        print()
        print("🔧 USO DE FERRAMENTAS:")
        print(f"   RAG: {s.requests_com_rag} ({100*s.requests_com_rag/max(1,s.total_requests):.1f}%)")
        print(f"   SQL: {s.requests_com_sql} ({100*s.requests_com_sql/max(1,s.total_requests):.1f}%)")
        print(f"   Agendamento: {s.requests_com_agendamento} ({100*s.requests_com_agendamento/max(1,s.total_requests):.1f}%)")

        if s.por_categoria:
            print()
            print("📁 POR CATEGORIA:")
            for cat, data in s.por_categoria.items():
                avg_ms = data["tempo_ms"] / max(1, data["total"])
                print(f"   {cat}: {data['sucesso']}/{data['total']} sucesso, {avg_ms:.0f}ms medio")

        print(f"{'='*60}\n")

    def save_results(self, output_path: str):
        """Salva resultados em CSV."""
        output_path = Path(output_path)

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            if not self.results:
                return

            # Campos para o CSV (exclui raw_response que e muito grande)
            fieldnames = [
                "test_id", "timestamp", "cliente_nome", "cliente_final_id",
                "mensagem", "categoria_teste", "resposta", "status_code",
                "tempo_resposta_ms", "ferramentas_usadas", "usou_rag",
                "usou_sql", "usou_agendamento", "erro", "thread_id"
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for r in self.results:
                row = asdict(r)
                row["ferramentas_usadas"] = ",".join(row["ferramentas_usadas"])
                del row["raw_response"]
                writer.writerow(row)

        print(f"💾 Resultados salvos em: {output_path}")


def create_sample_csv(output_path: str):
    """Cria um CSV de exemplo para testes."""
    sample_data = [
        # Studio J - Salao
        {"cliente_nome": "Studio J", "cliente_final_id": "maria_123", "mensagem": "Oi, quero agendar um corte para sabado", "categoria_teste": "agendamento"},
        {"cliente_nome": "Studio J", "cliente_final_id": "maria_123", "mensagem": "Quanto custa uma morena iluminada?", "categoria_teste": "preco"},
        {"cliente_nome": "Studio J", "cliente_final_id": "ana_456", "mensagem": "Preciso cancelar meu horario de amanha", "categoria_teste": "cancelamento"},
        {"cliente_nome": "Studio J", "cliente_final_id": "julia_789", "mensagem": "Quais cuidados devo ter depois de pintar o cabelo?", "categoria_teste": "rag_cuidados"},

        # Oficina Mendes
        {"cliente_nome": "Oficina Mendes", "cliente_final_id": "joao_111", "mensagem": "Meu carro ja ta pronto?", "categoria_teste": "status"},
        {"cliente_nome": "Oficina Mendes", "cliente_final_id": "pedro_222", "mensagem": "Quero fazer uma revisao preventiva", "categoria_teste": "agendamento"},
        {"cliente_nome": "Oficina Mendes", "cliente_final_id": "carlos_333", "mensagem": "Voces fazem alinhamento?", "categoria_teste": "servicos"},
        {"cliente_nome": "Oficina Mendes", "cliente_final_id": "jose_444", "mensagem": "Qual a garantia do servico?", "categoria_teste": "rag_garantia"},

        # Casa com Alma
        {"cliente_nome": "Casa com Alma", "cliente_final_id": "lucia_555", "mensagem": "Meu pedido ja foi enviado?", "categoria_teste": "status_pedido"},
        {"cliente_nome": "Casa com Alma", "cliente_final_id": "fernanda_666", "mensagem": "Voces tem almofadas de algodao?", "categoria_teste": "rag_produtos"},
        {"cliente_nome": "Casa com Alma", "cliente_final_id": "patricia_777", "mensagem": "Qual o prazo de troca?", "categoria_teste": "rag_politica"},

        # Dra. Beatriz Mendes
        {"cliente_nome": "Consultorio Dra. Beatriz Mendes", "cliente_final_id": "roberto_888", "mensagem": "Quero marcar uma consulta para avaliar manchas na pele", "categoria_teste": "agendamento"},
        {"cliente_nome": "Consultorio Dra. Beatriz Mendes", "cliente_final_id": "amanda_999", "mensagem": "Voces aceitam convenio Bradesco?", "categoria_teste": "rag_convenio"},
        {"cliente_nome": "Consultorio Dra. Beatriz Mendes", "cliente_final_id": "marcos_000", "mensagem": "Qual o valor da primeira consulta?", "categoria_teste": "rag_preco"},

        # Marcos Eletricista
        {"cliente_nome": "Marcos Eletricista", "cliente_final_id": "antonio_aaa", "mensagem": "Preciso trocar um chuveiro, quanto custa?", "categoria_teste": "orcamento"},
        {"cliente_nome": "Marcos Eletricista", "cliente_final_id": "silva_bbb", "mensagem": "A luz da minha casa fica caindo, pode vir ver?", "categoria_teste": "visita_tecnica"},
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cliente_nome", "cliente_final_id", "mensagem", "categoria_teste"])
        writer.writeheader()
        writer.writerows(sample_data)

    print(f"✅ CSV de exemplo criado: {output_path}")
    print(f"   {len(sample_data)} mensagens de teste")


def main():
    parser = argparse.ArgumentParser(
        description="Batch requests para testar o Atendente Vizu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Criar CSV de exemplo
  python batch_requests.py --create-sample

  # Executar com DB local (busca API keys automaticamente)
  python batch_requests.py --csv mensagens.csv

  # Executar com Supabase (producao)
  python batch_requests.py --csv mensagens.csv --supabase

  # Executar com DB custom
  python batch_requests.py --csv mensagens.csv --db-url 'postgresql://...'

  # Modo verbose com sleep maior
  python batch_requests.py --csv mensagens.csv --verbose --sleep 2.0

Variaveis de ambiente:
  DATABASE_URL       - URL do banco local
  SUPABASE_DB_URL    - URL do Supabase (producao)
        """
    )

    parser.add_argument("--csv", type=str, help="Caminho do CSV com mensagens de teste")
    parser.add_argument("--output", "-o", type=str, default="batch_results.csv", help="Arquivo de saida (default: batch_results.csv)")
    parser.add_argument("--api-url", type=str, default=None, help=f"URL da API (auto-detecta Docker vs host)")
    parser.add_argument("--db-url", type=str, help="URL do banco de dados para buscar API keys")
    parser.add_argument("--supabase", action="store_true", help="Usar Supabase (requer SUPABASE_DB_URL env)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Timeout em segundos (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_BETWEEN_REQUESTS, help=f"Sleep entre requests (default: {DEFAULT_SLEEP_BETWEEN_REQUESTS}s)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Modo verbose")
    parser.add_argument("--create-sample", action="store_true", help="Cria um CSV de exemplo")

    args = parser.parse_args()

    # Criar CSV de exemplo
    if args.create_sample:
        create_sample_csv("mensagens_teste.csv")
        return

    # Validar argumentos
    if not args.csv:
        parser.error("--csv e obrigatorio (ou use --create-sample para criar um exemplo)")

    # Determinar URL do banco
    db_url = None
    if args.supabase:
        db_url = os.environ.get("SUPABASE_DB_URL")
        if not db_url:
            parser.error("--supabase requer SUPABASE_DB_URL definido no ambiente")
        print("🌐 Usando Supabase (producao)")
    elif args.db_url:
        db_url = args.db_url
    else:
        db_url = os.environ.get("DATABASE_URL", LOCAL_DB_URL)
        print(f"🏠 Usando banco local: {db_url.split('@')[1] if '@' in db_url else db_url}")

    # Carregar API keys do banco
    try:
        api_keys = load_api_keys_from_db(db_url)
    except Exception as e:
        print(f"❌ Erro ao carregar API keys: {e}")
        print("   Certifique-se de que o banco esta acessivel e tem dados em cliente_vizu")
        sys.exit(1)

    if not api_keys:
        print("❌ Nenhuma API key encontrada no banco")
        sys.exit(1)

    # Detectar URL da API (Docker vs host)
    api_url = args.api_url or detect_api_url()
    print(f"🌐 API URL: {api_url}")

    # Executar batch
    requester = BatchRequester(
        api_url=api_url,
        api_keys=api_keys,
        timeout=args.timeout,
        verbose=args.verbose,
        sleep_between=args.sleep
    )

    try:
        requester.run_from_csv(args.csv)
        requester.print_stats()
        requester.save_results(args.output)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuario")
        requester.print_stats()
        requester.save_results(args.output)


if __name__ == "__main__":
    main()
