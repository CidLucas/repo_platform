# Monday.com API — Referência Prática para o Blu

Baseado na documentação oficial: https://developer.monday.com/api-reference/reference/about-the-api-reference
Última leitura: 22/mai/2026

---

## 1. Fundamentos

- API GraphQL. Endpoint único: `https://api.monday.com/v2`
- Header obrigatório: `Authorization: Bearer <token>` + `Content-Type: application/json`
- Scopes principais: `boards:read`, `boards:write`, `workspaces:read`
- Rate limits: 40 mutations/min para criação/duplicação de boards
- Versionamento de API: algumas features exigem versão explícita (ex: `2026-04`, `2026-07`) via header `API-Version`

---

## 2. Boards

### Buscar boards

```graphql
query {
  boards(
    limit: 20
    # board_kind: public  ← OMITIR para incluir boards privados
    # hierarchy_type omitido → retorna APENAS classic boards (não multi_level)
  ) {
    id
    name
    board_kind   # private | public | share
    type         # board | sub_items_board | document | custom_object
    groups { id title }
    columns { id title type }
  }
}
```

**⚠️ Pitfalls críticos:**
- `hierarchy_type` omitido → retorna só boards `classic` se nenhum ID for passado
- `board_kind: public` EXCLUI boards privados — usar sem esse filtro para pegar tudo
- Boards de subitems têm `type = sub_items_board`; boards normais têm `type = board`
- `workspace` / `workspace_id` retorna `null` para o workspace principal (Main)
- Campo `owner` (singular) está **DEPRECATED** — usar `owners`

### Filtrar boards de subitems

Forma robusta (não depende do nome):
```graphql
boards { type }
# Filtrar no código: if (board.type === 'sub_items_board') skip
```

Forma frágil atual (hardcoded PT-BR, evitar):
```ts
if (b.name?.toLowerCase().includes('subelementos de ')) return false
```

---

## 3. Groups

- Groups são **seções** dentro de um board
- Não podem ser query na raiz — sempre nested dentro de `boards`
- Para pegar items de um group específico: `boards { groups(ids: ["group_id"]) { items_page { ... } } }`

```graphql
query {
  boards(ids: [1234567890]) {
    groups {
      id
      title
      color
      position
      archived
      deleted
      items_page(limit: 100) { items { id name } }
    }
  }
}
```

---

## 4. Items — Paginação (items_page)

**Regra fundamental:** `items_page` NÃO pode ser query na raiz. Sempre nested em `boards` ou `groups`.

```graphql
query {
  boards(ids: [1234567890]) {
    items_page(
      limit: 100          # max: 500
      query_params: {
        rules: [
          { column_id: "status", compare_value: [1] }
        ]
        operator: and
      }
    ) {
      cursor              # null = não há mais items
      items {
        id
        name
        group { id title }
        column_values { id type text value }
      }
    }
  }
}
```

**Paginação com cursor:**
```graphql
query {
  next_items_page(limit: 100, cursor: "CURSOR_DO_REQUEST_ANTERIOR") {
    cursor
    items { id name }
  }
}
```

**⚠️ Pitfalls:**
- `cursor` e `query_params` são **mutuamente exclusivos** — usar `query_params` só na primeira chamada
- `hierarchy_scope_config: allItems` retorna items diretamente matches; `parentItems` (default) inclui parents de matches
- Para filtrar por pessoa: usar `"person-76543210"` (não ID numérico) com `any_of`

---

## 5. Column Values — Leitura

```graphql
items {
  column_values {
    id
    type
    text    # valor formatado para display
    value   # JSON string com dados brutos
    ... on TimelineValue {
      from
      to
      visualization_type
    }
    ... on DateValue {
      date
      time
    }
    ... on StatusValue {
      index
      label
      is_done
    }
    ... on PeopleValue {
      persons_and_teams { id kind }
    }
  }
}
```

---

## 6. Coluna Timeline (CRÍTICO para o Gantt)

**Tipo GraphQL:** `TimelineValue`

### Campos disponíveis
| Campo | Tipo | Descrição |
|---|---|---|
| `from` | `Date` | Data início (ISO 8601) ou null |
| `to` | `Date` | Data fim (ISO 8601) ou null |
| `text` | `String` | `"YYYY-MM-DD - YYYY-MM-DD"` ou `""` |
| `visualization_type` | `String` | `"milestone"` ou null |
| `value` | `JSON` | JSON raw: `{"from":"...","to":"...","changed_at":"..."}` |
| `is_leaf` | `Boolean!` | true = item real; false = rollup de parent |

### Leitura correta
```graphql
column_values {
  ... on TimelineValue {
    id
    from   # "2026-05-25"
    to     # "2026-06-05"
    text
    is_leaf
  }
}
```

### Escrita (update)
```graphql
mutation {
  change_multiple_column_values(
    board_id: 1234567890
    item_id: 9876543210
    column_values: "{\"timeline\":{\"from\":\"2026-05-25\",\"to\":\"2026-06-05\"}}"
  ) { id }
}
```

**⚠️ Pitfalls críticos:**
- `change_simple_column_value` NÃO funciona para timeline — usar `change_multiple_column_values`
- Em boards multi-level, colunas rollup de timeline precisam de `column_values(capabilities: [CALCULATED])`
- O campo `value` (JSON raw) contém `from`/`to` como strings — essa é a forma que extractMondayDate lia errado (type="date" vs type="timeline")
- `visualization_type: "milestone"` = item é um marco pontual, não um range

---

## 7. Coluna Date

**Tipo GraphQL:** `DateValue`

```graphql
... on DateValue {
  date    # "YYYY-MM-DD" ou ""
  time    # hora em timezone do user, ou ""
  text    # formatado
  value   # JSON raw
}
```

**Update:**
```graphql
# Simples (só data):
change_simple_column_value(value: "2026-06-15")

# Com hora (UTC):
change_simple_column_value(value: "2026-06-15 09:00:00")

# Via change_multiple:
column_values: "{\"date\":{\"date\":\"2026-06-15\",\"time\":\"09:00:00\"}}"
```

**⚠️ Diferença crítica com Timeline:**
- `DateValue.date` = string `"YYYY-MM-DD"` (ponto único no tempo)
- `TimelineValue.from` + `TimelineValue.to` = range de datas
- NO GANTT: a coluna que o board usa é `timeline`, não `date`. A função `extractMondayDate` lia `type="date"` — esse era o bug root cause.

---

## 8. Coluna Status

```graphql
... on StatusValue {
  index    # ID numérico do label (usar no update)
  label    # texto do label ("Em Progresso", "Concluído")
  is_done  # booleano
  label_style { color border }
}
```

**Update:**
```graphql
column_values: "{\"status\":{\"index\":1}}"
# ou
column_values: "{\"status\":{\"label\":\"Done\"}}"
```

**⚠️ Pitfall:** Em boards multi-level com rollup de status, o tipo é `BatteryValue`, não `StatusValue`.

---

## 9. Coluna People (Responsável)

```graphql
... on PeopleValue {
  persons_and_teams { id kind }  # kind: "person" | "team"
  text   # nomes separados por vírgula
}
```

**Update:**
```graphql
column_values: "{\"people\":{\"personsAndTeams\":[{\"id\":48202303,\"kind\":\"person\"}]}}"
```

**Filtro:**
```graphql
rules: [{ column_id: "people", compare_value: ["person-48202303"], operator: any_of }]
```

**⚠️ Update é replace-all** — se quiser adicionar sem remover, ler antes.

---

## 10. Query Completa — Pattern Blu (get-agenda-events)

```graphql
query {
  boards(limit: 20) {
    id
    name
    type
    groups {
      id
      title
      items_page(limit: 500) {
        items {
          id
          name
          group { id title }
          column_values {
            id
            type
            text
            value
            ... on TimelineValue { from to visualization_type is_leaf }
            ... on DateValue { date time }
            ... on StatusValue { index label is_done }
            ... on PeopleValue { persons_and_teams { id kind } }
          }
        }
      }
    }
  }
}
```

---

## 11. Troubleshooting — Bugs do Handoff

### Bug 1 — Rotinas como barras contínuas

**Root cause:** `get_unified_tasks` retorna `start_date = last_run_at`, `due_date = last_run_at + 7d`.

**Fix — 3 partes:**

**A) Migration SQL** (adicionar ao SELECT de client_routines):
```sql
cr.schedule_cron,
cr.frequency_days,
cr.next_run_at,
COALESCE(cr.next_run_at::date, CURRENT_DATE + 1) AS start_date,
COALESCE(cr.next_run_at::date, CURRENT_DATE + 1) AS due_date
```

**B) UnifiedTask interface** (TypeScript):
```ts
frequency_days?: number | null
schedule_cron?: string | null
next_run_at?: string | null
```

**C) MonthlyGantt.tsx** — expandRoutineOccurrences():
```ts
function expandRoutineOccurrences(routine: UnifiedTask, start: Date, end: Date): Date[] {
  if (!routine.frequency_days) return [new Date(routine.start_date)]
  const dates: Date[] = []
  let cur = new Date(routine.start_date)
  while (cur <= end) {
    if (cur >= start) dates.push(new Date(cur))
    cur = addDays(cur, routine.frequency_days)
  }
  return dates
}
// Cada ocorrência → pin vertical (linha + círculo), não barra
```

### Bug 2 — Projetos expandidos por padrão

```ts
// MonthlyGantt.tsx ~linha 273
const [expanded, setExpanded] = useState<Set<string>>(
  () => new Set(externalEvents.filter(e => e.type === 'project').map(e => e.id))
)
```
Revisitar quando houver muitos projetos.

### Bug 3 — Tarefas sem owner

Não é bug de código. Dado não preenchido no Monday. `extractMondayOwner` já suporta `type="multiple-person"`.

### Bug 4 — Filtro de subitems frágil

**Atual (frágil):**
```ts
if (b.name?.toLowerCase().includes('subelementos de ')) return false
```

**Robusto (usar `type` do board):**
```ts
if (b.type === 'sub_items_board') return false
if (b.name?.toLowerCase().includes('welcome to')) return false
```
O campo `type` está disponível na query de boards e é confiável independente do idioma.

---

## 12. Referências

- Boards: https://developer.monday.com/api-reference/reference/boards
- Groups: https://developer.monday.com/api-reference/reference/groups
- Items Page: https://developer.monday.com/api-reference/reference/items-page
- Timeline column: https://developer.monday.com/api-reference/reference/timeline
- Date column: https://developer.monday.com/api-reference/reference/date
- Status column: https://developer.monday.com/api-reference/reference/status
- People column: https://developer.monday.com/api-reference/reference/people
- Columns: https://developer.monday.com/api-reference/reference/columns
