# CORS Configuration Guide

## O que foi implementado

O data_ingestion_api agora possui configuração completa de CORS (Cross-Origin Resource Sharing) para permitir que frontends em diferentes origens façam requisições à API.

## Como funciona

### Configuração via Variáveis de Ambiente

#### Desenvolvimento Local
Para permitir requisições do seu frontend local (Vite rodando em `localhost:5173`):

```bash
# No arquivo .env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173
```

#### Produção
Para permitir apenas origens específicas em produção:

```bash
# No arquivo .env ou nas variáveis de ambiente do Cloud Run
CORS_ORIGINS=https://app.vizu.com.br,https://dashboard.vizu.com.br
```

#### Modo Desenvolvimento (Permite Tudo)
**⚠️ USE APENAS EM DESENVOLVIMENTO!**

```bash
CORS_ALLOW_ALL=true
```

Isso permite requisições de **qualquer** origem. **NUNCA use em produção!**

## Configuração no Cloud Run

Como você está rodando o serviço no Cloud Run e acessando do localhost, precisa configurar as variáveis de ambiente:

### Opção 1: Permitir localhost durante desenvolvimento

```bash
gcloud run services update data-ingestion-api \
  --set-env-vars="CORS_ORIGINS=http://localhost:5173,https://app.vizu.com.br" \
  --region=southamerica-east1
```

### Opção 2: Permitir todas as origens (APENAS PARA TESTES!)

```bash
gcloud run services update data-ingestion-api \
  --set-env-vars="CORS_ALLOW_ALL=true" \
  --region=southamerica-east1
```

### Opção 3: Configurar via Console do Cloud Run

1. Acesse o Cloud Run Console
2. Selecione o serviço `data-ingestion-api`
3. Clique em "Edit & Deploy New Revision"
4. Na seção "Variables & Secrets", adicione:
   - `CORS_ORIGINS`: `http://localhost:5173,https://app.vizu.com.br`
   - OU `CORS_ALLOW_ALL`: `true` (apenas para testes)
5. Clique em "Deploy"

## Testando CORS

### Teste 1: Verificar CORS Headers

```bash
# Simula uma requisição preflight (OPTIONS)
curl -X OPTIONS https://data-ingestion-api-858493958314.southamerica-east1.run.app/credentials/test-connection \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  -v
```

**Resposta esperada:**
```
< HTTP/2 200
< access-control-allow-origin: http://localhost:5173
< access-control-allow-methods: *
< access-control-allow-headers: *
< access-control-allow-credentials: true
```

### Teste 2: Fazer requisição real do browser

```javascript
// No console do browser
fetch('https://data-ingestion-api-858493958314.southamerica-east1.run.app/health', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(r => r.json())
.then(console.log)
.catch(console.error);
```

## Solução do seu problema atual

O erro que você está enfrentando:
```
No 'Access-Control-Allow-Origin' header is present on the requested resource
```

Acontece porque o Cloud Run não sabe que deve permitir `http://localhost:5173`.

**Solução Rápida:**

Execute este comando para permitir seu localhost:

```bash
gcloud run services update data-ingestion-api \
  --update-env-vars="CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://app.vizu.com.br" \
  --region=southamerica-east1
```

Ou, se quiser permitir tudo temporariamente para testes:

```bash
gcloud run services update data-ingestion-api \
  --update-env-vars="CORS_ALLOW_ALL=true" \
  --region=southamerica-east1
```

**⚠️ IMPORTANTE:** Depois dos testes, configure apenas as origens necessárias em produção!

## Boas Práticas

1. **Nunca use `CORS_ALLOW_ALL=true` em produção**
   - Apenas para desenvolvimento/testes locais
   - Em produção, liste explicitamente todas as origens permitidas

2. **Liste todas as origens necessárias**
   ```bash
   CORS_ORIGINS=https://app.vizu.com.br,https://dashboard.vizu.com.br,https://admin.vizu.com.br
   ```

3. **Para desenvolvimento local**
   - Use um `.env` file local com `CORS_ALLOW_ALL=true`
   - Não commite esse arquivo no git

4. **Para staging/produção**
   - Configure explicitamente via Cloud Run environment variables
   - Use apenas HTTPS (exceto localhost para dev)

## Troubleshooting

### Problema: Ainda recebo erro de CORS

**Solução 1:** Verifique se as variáveis de ambiente foram aplicadas
```bash
gcloud run services describe data-ingestion-api --region=southamerica-east1 --format="value(spec.template.spec.containers[0].env)"
```

**Solução 2:** Aguarde alguns segundos após o deploy
- O Cloud Run pode levar alguns segundos para aplicar as novas configurações

**Solução 3:** Force um novo deploy
```bash
gcloud run deploy data-ingestion-api --image=... --region=southamerica-east1
```

### Problema: Funciona no Postman mas não no browser

Isso é esperado! O Postman não aplica políticas CORS (é uma ferramenta de desenvolvimento).
Os browsers SIM aplicam CORS para proteger os usuários.

### Problema: Preflight request falhando

Verifique se o método OPTIONS está sendo permitido:
- O código já configura `allow_methods=["*"]` que inclui OPTIONS
- Certifique-se de que não há middleware bloqueando OPTIONS requests

## Logs para Debug

Para verificar se o CORS está sendo configurado corretamente, veja os logs:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=data-ingestion-api" --limit=50
```

Procure por:
```
Configurando CORS para as origens: ['http://localhost:5173', ...]
```

## Referências

- [FastAPI CORS Middleware](https://fastapi.tiangolo.com/tutorial/cors/)
- [MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Cloud Run Environment Variables](https://cloud.google.com/run/docs/configuring/environment-variables)
