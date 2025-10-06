# 1. Inicia a partir da imagem oficial do Ollama.
# Usar a tag 'latest' é bom para começar, mas em produção podemos fixar uma versão.
FROM ollama/ollama:latest

# 2. Cria um diretório de trabalho dentro da imagem para organizar nossos arquivos.
WORKDIR /app

# 3. Copia os arquivos de configuração do nosso serviço para dentro da imagem.
# Por enquanto, apenas o Modelfile.
COPY Modelfile /app/Modelfile

# 4. Copia o script de inicialização que orquestrará a criação dos modelos.
# (Criaremos este script no próximo passo).
COPY entrypoint.sh /app/entrypoint.sh

# 5. Dá permissão de execução para o nosso script de inicialização.
RUN chmod +x /app/entrypoint.sh

# 6. Expõe a porta padrão do Ollama para que outros serviços possam se conectar.
EXPOSE 11434

# 7. Define o nosso script como o comando que será executado quando um container for iniciado.
ENTRYPOINT [ "/app/entrypoint.sh" ]