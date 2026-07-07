BKL-034: Multi-Upload — uploadMulti() para múltiplos arquivos

Goal: Adicionar suporte a upload em lote na knowledge base via funcao uploadMulti() em knowledgeBaseService.ts.

ACs:
- AC1: uploadMulti(files: File[]) exportada como async function
- AC2: Suporte a pastas via webkitdirectory ou drop de diretorio
- AC3: Cada arquivo da fila chama o fluxo de processamento individual

Teste RED: tests/behaviors/test_b1_upload_multi.py
Issue: #206 (F-3: Upload e Navegacao de Documentos)
Implementacao alvo: apps/blu_v3/src/services/knowledgeBaseService.ts

Latest summary:
Falha na validação (testes não passam)

Comments (4):
  [2026-06-26 17:44] default: BLOCKED: Falha na validação (testes não passam)
  [2026-06-26 17:46] default: BLOCKED: Aguardando 3 in-progress terminarem (WIP limit 3)
  [2026-06-26 18:02] factory-coder: ## GREEN: BKL-034 — uploadMulti() implementado

**PR**: https://github.com/CidLucas/repo_platform/pull/234
**Branch**: feat/bkl-034-upload-multi
**Commit**: 17b25427

### Implementation
- `export async function uploadMulti(files: File[], clientId, source?, options?): Promise<string[]>`
- Itera sobre `File[]` e chama `uploadFile()` (dispatcher simple/complex) para cada arquivo
- Compatível com `webkitdirectory` e directory drops

### Test Results
- `tests/behaviors/test_b1_upload_multi.py` — **1/1 PASSED** (GREEN)

### Files changed
- `apps/blu_v3/src/services/knowledgeBaseService.ts` (+16 linhas)

### Metadata
```json
{
  "changed_files": ["apps/blu_v3/src/services/knowledgeBaseService.ts"],
  "tests_run": 1,
  "tests_passed": 1,
  "diff_path": "apps/blu_v3/src/services/knowledgeBaseService.ts",
  "pr_number": 234,
  "commit": "17b25427"
}
```
  [2026-06-26 18:12] default: BLOCKED: Falha na validação (testes não passam)

## Instrução
Implemente o código GREEN mínimo para fazer o teste RED passar. Não adicione funcionalidades extras. Crie um PR com as alterações.