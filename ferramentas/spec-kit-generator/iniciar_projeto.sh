set -e # Encerra o script se qualquer comando falhar

if [ -z "$1" ]; then
  echo "❌ Erro: Você precisa fornecer um nome para o projeto."
  echo "Uso: $0 NOME_DO_PROJETO"
  exit 1
fi

PROJECT_NAME=$1
TEMP_DIR="../temp_spec_kit_${PROJECT_NAME}"

if [ -d "$TEMP_DIR" ]; then
  echo "⚠️ Aviso: O diretório '$TEMP_DIR' já existe."
  read -p "Você gostaria de removê-lo e começar de novo? (s/n): " confirm
  if [[ "$confirm" == "s" || "$confirm" == "S" ]]; then
    echo "Removendo diretório existente..."
    rm -rf "$TEMP_DIR"
  else
    echo "Operação cancelada."
    exit 0
  fi
fi

echo "🚀 Iniciando a configuração do ambiente para '$PROJECT_NAME'..."
echo "1. Criando diretório de trabalho temporário em: $TEMP_DIR"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "2. Criando ambiente virtual com 'uv' (para futuras dependências do projeto)..."
uv venv

echo "✅ Ambiente pronto!"
echo "---"
echo "Agora, vamos iniciar o Gemini CLI para começar a especificação."
echo "Use os comandos do Spec-Kit (ex: /speckit.init) no terminal do Gemini."
echo "---"

# Ativa o ambiente virtual para que o Gemini CLI o reconheça como o contexto do projeto
source .venv/bin/activate

gemini

echo "✨ Sessão do Gemini encerrada."
read -p "Deseja remover o diretório de trabalho temporário ('$TEMP_DIR')? (s/n): " cleanup_confirm
if [[ "$cleanup_confirm" == "s" || "$cleanup_confirm" == "S" ]]; then
  echo "Limpando e removendo $TEMP_DIR..."
  cd ..
  rm -rf "$TEMP_DIR"
  echo "Limpeza concluída."
else
  echo "O diretório de trabalho foi mantido em $TEMP_DIR para referência."
fi

echo "Processo finalizado."