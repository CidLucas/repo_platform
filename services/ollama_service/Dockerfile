# 1. Inicia a partir da imagem oficial do Ollama.
FROM ollama/ollama:latest

# --- CORREÇÃO APLICADA AQUI ---
# Instala o 'curl' para que nosso script de health check possa funcionar.
# Usamos 'apt-get' que é o gerenciador de pacotes comum em imagens baseadas em Debian/Ubuntu.
RUN apt-get update && apt-get install -y curl

# 2. Cria um diretório de trabalho dentro da imagem.
WORKDIR /app

# 3. Copia os arquivos de configuração.
COPY services/ollama_service/Modelfile /app/Modelfile
COPY services/ollama_service/entrypoint.sh /app/entrypoint.sh

# 4. Dá permissão de execução para o nosso script.
RUN chmod +x /app/entrypoint.sh

# 5. Expõe a porta padrão do Ollama.
EXPOSE 11434

# 6. Define o nosso script como o comando de entrada.
ENTRYPOINT [ "/app/entrypoint.sh" ]