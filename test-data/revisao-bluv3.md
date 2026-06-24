# Revisão Blu v3 — Onboarding de Clientes Fake

> **Arquivo vivo de observações.** Cada bug, desconforto, inconsistência ou sugestão
> encontrada durante o onboarding dos clientes fake deve ser registrada aqui.
>
> Depois de finalizar todos os testes, este arquivo vira o backlog de melhorias
> pré-produção.

---

## Setup

### Clientes Fake

| Persona | E-mail | Nome | Senha |
|---|---|---|---|
| 🎨 Carolina Mendes (Designer) | `carolina.design@test.blu.sh` | Carolina Mendes de Oliveira | `Test@2026!` |
| 🍽️ Lúcia's Food (Buffet) | `lucia.buffet@test.blu.sh` | Lúcia Alves Freitas | `Test@2026!` |
| 🏢 NovaTech TI | `joao.novatech@test.blu.sh` | João Batista Nogueira | `Test@2026!` |

### Arquivos de teste por persona

```
📁 test-data/personas/
│
├── carolina-design/
│   ├── historico-do-negocio.md          ← descritivo completo
│   ├── notas-fiscais/
│   │   ├── nfs_servicos_prestados.csv   ← 37 NFs de serviço
│   │   └── nfs_compras_despesas.csv     ← 56 NFs de compra
│   ├── planilhas/
│   │   └── planilha_controle_carol.xlsx ← 2 abas (Projetos + Financeiro)
│   ├── propostas-orcamentos/
│   │   └── orcamentos.csv
│   └── documentos-ruido/
│       ├── nfs_escaneadas/              ← 3 NFSe PDF
│       ├── extratos/                    ← extrato_nubank + itau CSV
│       ├── contratos/                   ← contrato_carolina_lucia_assinado.pdf
│       ├── divulgacao/                  ← flyer_portfolio_carolina.pdf
│       ├── propostas_antigas/           ← proposta_technova_28000.pdf
│       ├── imagens/                     ← logo_placeholder.png
│       └── *.txt                        ← contatos, anotações, etc.
│
├── lucia-buffet/
│   ├── historico-do-negocio.md
│   ├── notas-fiscais/
│   │   ├── nfs_vendas_servicos.csv      ← 47 NFs de venda
│   │   └── nfs_compras_insumos.csv      ← 41 NFs de compra
│   ├── planilhas/
│   │   └── controle_fornecedores.xlsx   ← 3 abas
│   ├── propostas-orcamentos/
│   │   └── orcamentos_eventos.csv
│   └── documentos-ruido/
│       ├── nfs_escaneadas/              ← 3 DANFE PDF
│       ├── extratos/                    ← extrato_nubank + itau CSV
│       ├── divulgacao/                  ← cardapio_lucias_food.pdf + flyer
│       ├── imagens/                     ← logo_placeholder.png
│       └── *.txt                        ← checklist, contrato, receita, etc.
│
└── novatech-ti/
    ├── historico-do-negocio.md
    ├── notas-fiscais/
    │   ├── nfs_vendas_servicos_recorrentes.csv ← 131 NFs
    │   ├── nfs_vendas_hardware.csv             ← 9 NFs
    │   └── nfs_compras_estoque.csv             ← 30 NFs
    ├── planilhas/
    │   ├── fluxo_caixa_2025.xlsx
    │   └── comissoes_vendas.xlsx
    ├── propostas-orcamentos/
    │   └── propostas_comerciais.csv
    └── documentos-ruido/
        ├── nfs_escaneadas/              ← 3 DANFE PDF
        ├── extratos/                    ← extrato_nubank + itau CSV
        ├── contratos/                   ← contrato_novatech_autopecas_assinado.pdf
        ├── divulgacao/                  ← flyer_servicos_novatech.pdf
        ├── propostas_antigas/           ← proposta_construtora_nuvem_45000.pdf
        ├── imagens/                     ← logo_placeholder.png
        └── *.txt                        ← senhas, estoque, chamados, etc.
```

---

## Log de Observações

### Formato

```markdown
### [YYYY-MM-DD HH:MM] — [Persona] — [Etapa do onboarding]
**Tipo:** bug | ux | infra | missing | suggestion
**Descrição:** ...
**Impacto:** ...
**Sugestão:** ...
```

---

<!-- NOVAS OBSERVAÇÕES AQUI ⬇️ -->
