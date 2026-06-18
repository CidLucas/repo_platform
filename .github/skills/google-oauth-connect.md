# Google OAuth Connect (Admin UI)

Use este padrão sempre que precisar integrar Google Calendar/Drive no admin Blu.

## Caminho feliz
1. Front chama `connectGoogleCalendar()` em `apps/blu_v3/src/api/agenda.ts`.
2. Ele POSTa para `/functions/v1/google-oauth-start` com o scope desejado.
3. O start SEMPRE injeta `openid` e `userinfo.email` nos scopes, mesmo que o envie apenas `calendar.readonly`.
4. Google redireciona para `/functions/v1/google-oauth-callback`.
5. Callback troca code por token, busca `/oauth2/v2/userinfo`, salva em `integration_tokens` e habilita `calendar_settings`.
6. App lista contas por `list_integration_accounts`.

## Regras
- Não confiar em `expires_at` para Google OAuth; o schema atual não guarda esse campo em `integration_tokens`.
- Não usar PKCE; fluxo é code exchange server-side.
- Não reutilizar `code` antigo; fluxo novo gera novo code.
- Não devolver `Location` vazio; sempre cair em URL conhecida com `google_error` explícito.

## Arquivos
- `supabase/functions/google-oauth-start/index.ts`
- `supabase/functions/google-oauth-callback/index.ts`
- `apps/blu_v3/src/api/agenda.ts`
