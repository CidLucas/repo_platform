# Issue 11: Estrategia Room — Document Templates from Design System

## Goal
Integrate the 8 design system HTML templates into the Estrategia Room's Documentos tab, allowing users to create documents from pre-designed templates.

## What to build

### 1. Template selector in Documentos tab
File: `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`

Add a template selector UI above the editor. When the user clicks "+ Novo Documento", show a grid of template options instead of just creating a blank doc.

Template options (use the design system HTML files as a reference for names/icons):
- Fechamento Mensal
- Fluxo de Caixa
- Proposta Comercial
- Plano Estrategico
- OKR
- Ata de Reuniao
- SWOT
- Invoice

Each template card shows: icon + name + brief description.
Clicking a template pre-populates the editor with the template structure (markdown).

### 2. Template markdown content
For each template, provide initial markdown content that mirrors the HTML structure from the design system:

```typescript
const DOC_TEMPLATES: Record<string, string> = {
  'fechamento-mensal': `# Relatório de Fechamento Mensal\n\n## Resumo Executivo\n\n[Resumo do mês...]\n\n## Receitas\n\n| Linha | Valor | % |\n|---|---|---|\n| SaaS Corporativo | R$ 0 | 0% |\n\n## Despesas\n\n| Categoria | Valor | % |\n|---|---|---|\n| Infraestrutura | R$ 0 | 0% |\n\n## KPIs\n\n- Margem Bruta: 0%\n- Margem EBITDA: 0%\n- Margem Líquida: 0%\n- MRR: R$ 0`,
  'fluxo-caixa': `# Fluxo de Caixa\n\n## Atividades Operacionais\n\n- Lucro Líquido: R$ 0\n- Depreciação: R$ 0\n\n## Atividades de Investimento\n\n- CAPEX: R$ 0\n\n## Atividades de Financiamento\n\n- Empréstimos: R$ 0\n\n## Saldo Final: R$ 0`,
  'proposta-comercial': `# Proposta Comercial\n\n## Escopo\n\n- Item 1\n- Item 2\n\n## Investimento\n\n| Item | Valor |\n|---|---|\n| Licença | R$ 0 |\n| Implantação | R$ 0 |\n\n## Condições\n\n- Pagamento: ...\n- Prazo: ...`,
  'plano-estrategico': `# Plano Estratégico\n\n## Visão\n\n[Declaração de visão]\n\n## Missão\n\n[Declaração de missão]\n\n## Objetivos\n\n1. **Objetivo 1**\n2. **Objetivo 2**\n3. **Objetivo 3**\n\n## KPIs\n\n| Métrica | Meta | Atual |\n|---|---|---|\n| MRR | R$ 0 | R$ 0 |\n| NPS | 0 | 0 |`,
  'okr': `# OKR\n\n## Objective\n\n[Descrição do objetivo]\n\n## Key Results\n\n- KR1: [descrição] — 0%\n- KR2: [descrição] — 0%\n- KR3: [descrição] — 0%\n\n## Owner: [Nome]`,
  'ata-reuniao': `# Ata de Reunião\n\n**Data:** __/__/____\n**Participantes:**\n\n## Pauta\n\n1. \n2. \n\n## Discussões\n\n### 1. \n\n### 2. \n\n## Ações\n\n| # | Ação | Responsável | Prazo |\n|---|---|---|---|\n| 1 | | | |`,
  'swot': `# Análise SWOT\n\n## Forças (Strengths)\n\n-\n\n## Fraquezas (Weaknesses)\n\n-\n\n## Oportunidades (Opportunities)\n\n-\n\n## Ameaças (Threats)\n\n-`,
  'invoice': `# Fatura\n\n**Emitente:** Blu Tecnologia S.A.\n**Cliente:** [Nome do Cliente]\n\n## Itens\n\n| Item | Qtd | Valor Unit. | Total |\n|---|---|---|---|\n| | | R$ 0 | R$ 0 |\n\n**Total: R$ 0,00**`,
}
```

### 3. Add Sparkline to KPI cells
In the same file, find the `estrategiaMetrics.map` KPI rendering block and add `<Sparkline>` after the delta text:
```tsx
import { Sparkline } from '../../components/shared/Charts'

// Inside the KPI cell:
<Sparkline 
  data={[30, 45, 38, 52, 48, 61, 55, 68, 72, 65, 78, 84]} 
  width={100} height={24} 
  color={deltaColor} 
/>
```

### Files
- `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`

### Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
