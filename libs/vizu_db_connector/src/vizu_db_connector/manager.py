import os
import sys
import argparse
import subprocess
from pathlib import Path
from alembic.config import Config
from alembic import command
from datetime import datetime
from dotenv import load_dotenv

# Definindo caminhos
CURRENT_DIR = Path(__file__).parent
LIB_ROOT = CURRENT_DIR.parent.parent  # libs/vizu_db_connector
PROJECT_ROOT = LIB_ROOT.parent.parent  # raiz do monorepo

# Carrega variáveis do .env (se existir)
# override=False garante que variáveis do sistema/terminal tenham prioridade
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=False)

ALEMBIC_INI = LIB_ROOT / "alembic.ini"
SUPABASE_MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"


def get_db_url(args=None):
    """
    Recupera a URL do banco com prioridade:
    1. Flag --db na linha de comando
    2. Variável de ambiente do sistema (export DATABASE_URL=...)
    3. Arquivo .env na raiz do projeto
    """
    # 1. Tenta pegar do argumento --db
    if args and hasattr(args, "db") and args.db:
        return args.db

    # 2. Tenta pegar do ambiente já carregado
    url = os.getenv("DATABASE_URL")

    # 3. Se ainda não achou, força a leitura do .env novamente (debug)
    if not url:
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            # override=True força a atualização do os.environ com o que está no arquivo
            load_dotenv(dotenv_path=env_path, override=True)
            url = os.getenv("DATABASE_URL")

    if not url:
        print("\n❌ ERRO: DATABASE_URL não encontrada.")
        print(f"   Tentamos ler de: {PROJECT_ROOT / '.env'}")
        sys.exit(1)

    return url


def run_alembic_cmd(args):
    """Configura e roda comandos do Alembic."""
    alembic_cfg = Config(str(ALEMBIC_INI))
    url = get_db_url(args)
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    alembic_cfg.set_main_option("script_location", str(LIB_ROOT / "alembic"))
    return alembic_cfg


def cmd_migrate(args):
    """Aplica migrações."""
    url = get_db_url(args)
    print(
        f"🔄 Aplicando migrações em: {url.split('@')[-1]}"
    )  # Mostra apenas o host/db para segurança
    cfg = run_alembic_cmd(args)
    command.upgrade(cfg, "head")
    print("✅ Migrações aplicadas com sucesso!")


def cmd_makemigrations(args):
    """Cria uma nova revisão."""
    cfg = run_alembic_cmd(args)
    command.revision(cfg, message=args.message, autogenerate=True)
    print("✅ Arquivo de revisão gerado.")


def cmd_seed(args):
    """Roda os scripts de seed."""
    try:
        from .cli.seed import run_seed

        url = get_db_url(args)
        print(f"🌱 Semeando banco de dados em: {url.split('@')[-1]}")
        run_seed(url)
    except ImportError as e:
        print(f"⚠️  Erro de importação: {e}")


def cmd_export_supabase(args):
    """Gera o SQL para o Supabase."""
    print("📦 Exportando migração para formato Supabase SQL...")

    # Para export, usamos o ENV ou args, mas precisamos passar pro subprocesso
    target_url = get_db_url(args)
    env_copy = os.environ.copy()
    env_copy["DATABASE_URL"] = target_url

    cmd = [
        "poetry",
        "run",
        "alembic",
        "-c",
        str(ALEMBIC_INI),
        "upgrade",
        "head",
        "--sql",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(LIB_ROOT), env=env_copy
        )

        if result.returncode != 0:
            print(f"❌ Erro ao gerar SQL via Alembic:\n{result.stderr}")
            return

        sql_content = result.stdout

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        name = args.name.replace(" ", "_").lower() if args.name else "auto_migration"
        filename = f"{timestamp}_{name}.sql"
        file_path = SUPABASE_MIGRATIONS_DIR / filename

        SUPABASE_MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as f:
            f.write(f"-- Gerado via vizu-db export-supabase em {datetime.now()}\n")
            f.write(sql_content)

        print(f"✅ Arquivo gerado: supabase/migrations/{filename}")

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


def main():
    parser = argparse.ArgumentParser(description="Vizu DB Manager CLI")
    # Adiciona argumento global --db
    parser.add_argument(
        "--db", help="URL de conexão (sobrescreve .env)", required=False
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="Aplica migrações pendentes")

    parser_make = subparsers.add_parser("makemigrations", help="Gera nova revisão")
    parser_make.add_argument("message", help="Mensagem da migração")

    # Seed agora aceita argumentos globais (como --db) herdados ou explícitos se quisermos
    subparsers.add_parser("seed", help="Popula o banco")

    parser_exp = subparsers.add_parser(
        "export-supabase", help="Exporta SQL para Supabase"
    )
    parser_exp.add_argument("--name", help="Nome do arquivo", default="update")

    args = parser.parse_args()

    if args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "makemigrations":
        cmd_makemigrations(args)
    elif args.command == "seed":
        cmd_seed(args)
    elif args.command == "export-supabase":
        cmd_export_supabase(args)


if __name__ == "__main__":
    main()
