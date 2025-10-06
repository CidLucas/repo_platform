#!/bin/sh

# Garante que o script pare se qualquer comando falhar
set -e

echo "Iniciando o servidor Ollama em segundo plano..."
# Inicia o processo principal do Ollama em background para que possamos executar outros comandos
/bin/ollama serve &

# Armazena o ID do processo (PID) do servidor Ollama
pid=$!

echo "Aguardando o servidor Ollama ficar pronto..."
# Loop de verificação para garantir que o servidor esteja no ar antes de prosseguir
while ! curl -s -o /dev/null http://localhost:11434; do
  echo "Aguardando..."
  sleep 1
done

echo "Servidor Ollama detectado. Preparando modelos..."

# --- ESTRATÉGIA DE MODELOS PARA O MVP ---
# Usa o Modelfile que copiamos para a imagem para criar nosso modelo customizado.
# O comando 'ollama create' analisa o Modelfile, baixa o modelo base (se necessário)
# e cria um novo modelo com o nome que especificamos.
echo "Criando modelo 'vizu-llama3.2-mvp' a partir do Modelfile..."
ollama create vizu-llama3.2-mvp -f /app/Modelfile

echo "Modelos prontos para servir."

# Traz o processo do servidor Ollama para o primeiro plano para que o container não termine.
# O 'wait' aguarda o processo com o PID armazenado finalizar (o que nunca acontecerá,
# a menos que o servidor Ollam caia), mantendo o container ativo.
wait $pid