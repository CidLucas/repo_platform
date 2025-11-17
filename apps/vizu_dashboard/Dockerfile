# Estágio 1: Builder - Instala dependências e gera os arquivos estáticos
FROM node:20-alpine as builder

# Define o diretório de trabalho
WORKDIR /app

# 1. COPIA os arquivos de manifesto de dependências
COPY package.json package-lock.json ./

# 2. INSTALA as dependências do projeto
RUN npm install

# 3. COPIA todo o código-fonte da aplicação
COPY . .

# 4. EXECUTA o build de produção
# Isso irá gerar a pasta /dist com os arquivos otimizados
RUN npm run build

# -----------------------------------------------------

# Estágio 2: Final - Apenas o Runtime com Nginx
FROM nginx:stable-alpine

# 1. COPIA os arquivos estáticos gerados no estágio de build
# O Nginx por padrão serve arquivos de /usr/share/nginx/html
COPY --from=builder /app/dist /usr/share/nginx/html

# 2. REMOVE a configuração padrão do Nginx
RUN rm /etc/nginx/conf.d/default.conf

# 3. COPIA o arquivo de configuração customizado para o Nginx
# Este arquivo será criado a seguir e é essencial para o roteamento do React
COPY nginx.conf /etc/nginx/conf.d

# 4. EXPÕE a porta 80, que o Nginx usa por padrão
EXPOSE 80

# 5. DEFINE o comando para iniciar o servidor Nginx
CMD ["nginx", "-g", "daemon off;"]
