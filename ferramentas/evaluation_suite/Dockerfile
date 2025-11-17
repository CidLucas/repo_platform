# Estágio 1: Builder - Responsável por instalar as dependências
FROM python:3.11-slim as builder

# Instala o Poetry (nosso gerenciador de pacotes padrão)

# Configura o Poetry para não criar virtualenvs fora do projeto, facilitando a cópia
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR /app
RUN pip install poetry

# 1. COPIE as 'libs' primeiro. Este é o passo crucial para o cache do Docker no monorepo.
#    Se as libs não mudam, este layer não é reconstruído.
COPY ./libs ./libs

# 2. COPIE os arquivos de projeto da ferramenta para sua estrutura espelhada.
#    Isso garante que o Poetry encontre as dependências locais (libs).
COPY ./ferramentas/evaluation_suite/pyproject.toml ./ferramentas/evaluation_suite/poetry.lock* ./ferramentas/evaluation_suite/

# 3. MUDE o WORKDIR para o diretório da ferramenta.
WORKDIR /app/ferramentas/evaluation_suite

# 4. INSTALE as dependências.
#    O Poetry irá instalar tanto os pacotes do PyPI quanto as libs locais.
#    --no-root para não instalar a própria evaluation_suite, apenas suas dependências.
RUN poetry install --no-root


# Estágio 2: Final - Responsável por criar a imagem de execução leve
FROM python:3.11-slim

WORKDIR /app

# 5. COPIE o ambiente virtual (.venv) criado no estágio de builder.
COPY --from=builder /app/ferramentas/evaluation_suite/.venv ./.venv

# 6. ATIVE o ambiente virtual adicionando o diretório de binários ao PATH.
#    Isso garante que os comandos (python, streamlit, etc.) usem os pacotes instalados.
ENV PATH="/app/.venv/bin:$PATH"

# 7. COPIE o código fonte da aplicação e das libs necessárias para a execução.
COPY ./ferramentas/evaluation_suite/src ./src
COPY ./libs ./libs

# 8. CONFIGURE O PYTHONPATH.
#    Essencial para que o Python encontre os módulos das nossas bibliotecas internas no monorepo.
#    Aponta para o 'src' de cada lib que a ferramenta utiliza.
ENV PYTHONPATH="/app/src:/app/libs/vizu_db_connector/src:/app/libs/vizu_shared_models/src"

# 9. DEFINA o comando de execução da aplicação.
#    Conforme a especificação, a interface será uma aplicação Streamlit.
CMD ["streamlit", "run", "src/evaluation_suite/main.py"]