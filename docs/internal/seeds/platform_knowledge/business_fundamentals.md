# Fundamentos de Negócio e Análise Financeira

## 1. KPIs Financeiros Essenciais

### Receita e Faturamento
- **Receita Bruta**: Total faturado antes de impostos e deduções.
- **Receita Líquida**: Receita bruta - impostos sobre vendas - devoluções - descontos.
- **ARR (Annual Recurring Revenue)**: Receita recorrente anualizada (SaaS).
- **MRR (Monthly Recurring Revenue)**: Receita recorrente mensal (SaaS).
- **ARPU (Average Revenue Per User)**: Receita média por usuário ativo.

### Rentabilidade
- **Margem Bruta**: (Receita Líquida - CPV) / Receita Líquida × 100.
  - Referência: >50% para SaaS, 20-40% para varejo, 30-50% para indústria.
- **Margem Operacional (EBIT)**: Lucro operacional / Receita Líquida × 100.
- **Margem Líquida**: Lucro líquido / Receita Líquida × 100.
- **Margem EBITDA**: EBITDA / Receita Líquida × 100.
  - EBITDA = Lucro operacional + Depreciação + Amortização.

### Liquidez
- **Liquidez Corrente**: Ativo circulante / Passivo circulante.
  - > 1.0 = pode honrar obrigações de curto prazo.
  - < 1.0 = risco de insolvência.
- **Liquidez Seca**: (Ativo circulante - Estoques) / Passivo circulante.
- **Liquidez Imediata**: Disponível / Passivo circulante.

### Endividamento
- **Dívida Líquida / EBITDA**: Capacidade de pagamento da dívida.
  - < 2x = saudável | 2-3x = atenção | > 3x = risco alto.
- **Grau de Endividamento**: Passivo total / Ativo total.
- **Cobertura de Juros**: EBITDA / Despesas financeiras.

## 2. Unit Economics

### CAC — Custo de Aquisição de Cliente
- **Fórmula**: (Investimento Marketing + Vendas) / Novos Clientes no período.
- **Inclui**: Mídia paga, salários de SDR/AE, ferramentas de marketing, comissões.
- **Payback do CAC**: Meses para recuperar o investimento = CAC / Receita mensal por cliente.
  - Ideal: < 12 meses.

### LTV — Lifetime Value (Valor do Tempo de Vida do Cliente)
- **Fórmula simples**: ARPU mensal × Margem bruta × Tempo médio de vida (meses).
- **Fórmula com churn**: ARPU mensal × Margem bruta / Taxa de churn mensal.
- **Regra LTV/CAC**:
  - < 1x = operação insustentável (perde dinheiro por cliente).
  - 1-3x = operação frágil.
  - 3-5x = operação saudável (ideal).
  - > 5x = pode estar sub-investindo em crescimento.

### Churn (Taxa de Cancelamento)
- **Churn de clientes**: Clientes perdidos / Clientes no início do período.
- **Churn de receita (Revenue Churn)**: MRR perdido / MRR no início do período.
- **Net Revenue Retention (NRR)**: (MRR início + expansão - contração - churn) / MRR início.
  - > 100% = crescimento orgânico (upsell compensa churn).
  - Benchmarks SaaS: >120% é excelente, >100% é bom, <90% é preocupante.

### Ticket Médio
- **Fórmula**: Receita total / Número de transações.
- **Aumento de ticket**: Upsell, cross-sell, bundles, ancoragem de preço.

## 3. Demonstrações Financeiras

### DRE — Demonstração do Resultado do Exercício
```
Receita Bruta
(-) Deduções (impostos, devoluções, abatimentos)
= Receita Líquida
(-) CPV/CMV (Custo dos Produtos Vendidos / Custo da Mercadoria Vendida)
= Lucro Bruto
(-) Despesas Operacionais
    (-) Despesas administrativas
    (-) Despesas comerciais (marketing, vendas)
    (-) Despesas gerais
= Lucro Operacional (EBIT)
(+/-) Resultado Financeiro (receitas - despesas financeiras)
= Lucro Antes do IR (LAIR)
(-) IRPJ + CSLL
= Lucro Líquido
```

### Balanço Patrimonial
- **Ativo = Passivo + Patrimônio Líquido** (equação fundamental).
- **Ativo Circulante**: Caixa, contas a receber, estoques, aplicações de curto prazo.
- **Ativo Não Circulante**: Imobilizado (máquinas, imóveis), intangível (marcas, softwares), investimentos.
- **Passivo Circulante**: Fornecedores, empréstimos CP, salários, impostos a pagar.
- **Passivo Não Circulante**: Empréstimos LP, debêntures.
- **Patrimônio Líquido**: Capital social, reservas, lucros acumulados.

### DFC — Demonstração do Fluxo de Caixa
- **Operacional**: Resultado das operações do negócio (principal fonte de caixa saudável).
- **Investimento**: Compra/venda de ativos, CAPEX.
- **Financiamento**: Empréstimos, distribuição de dividendos, aumento de capital.
- **Burn Rate**: Taxa mensal de consumo de caixa (startups).
- **Runway**: Caixa disponível / Burn Rate mensal = meses até acabar.

## 4. Forecasting (Previsão)

### Métodos Top-Down
- Parte do mercado total (TAM) → mercado endereçável (SAM) → participação esperada (SOM).
- **TAM**: Total Addressable Market.
- **SAM**: Serviceable Addressable Market.
- **SOM**: Serviceable Obtainable Market (realista).

### Métodos Bottom-Up
- Parte de dados operacionais concretos (leads, conversão, ticket médio).
- **Fórmula**: Receita = Leads × Taxa de conversão × Ticket médio × Frequência.

### Cenários
- **Base (mais provável)**: Premissas realistas baseadas em histórico.
- **Otimista (bull)**: +20-30% sobre o base (condições favoráveis).
- **Pessimista (bear)**: -20-30% sobre o base (cenário adverso).
- **Análise de sensibilidade**: Variar uma premissa-chave mantendo as demais fixas.

### Forecasting de Séries Temporais
- Usar dados de pelo menos 2-3 ciclos completos (ex: 2-3 anos para capturar sazonalidade anual).
- Considerar variáveis exógenas: feriados, eventos, campanhas, sazonalidade.
- Validar com holdout: Treinar em 80% histórico, validar nos 20% restantes.
- Métricas de previsão: MAPE < 20% é geralmente aceitável em negócios.

## 5. Análise de Rentabilidade

### Ponto de Equilíbrio (Break-Even)
- **Em unidades**: Custos Fixos / (Preço unitário - Custo variável unitário).
- **Em receita**: Custos Fixos / Margem de contribuição percentual.
- **Margem de contribuição**: Preço - Custos variáveis.

### Análise de Pareto (80/20)
- 80% da receita vem de 20% dos clientes.
- 80% dos problemas vêm de 20% das causas.
- **Aplicações**: Priorização de clientes, foco em produtos mais rentáveis, identificação de gargalos.

### Análise ABC
- **A**: 20% dos itens = 80% do valor (alta prioridade).
- **B**: 30% dos itens = 15% do valor (média prioridade).
- **C**: 50% dos itens = 5% do valor (baixa prioridade).
- **Uso**: Gestão de estoque, priorização de clientes, alocação de recursos.

## 6. Métricas de Crescimento

### CAGR — Taxa Composta de Crescimento Anual
- **Fórmula**: (Valor final / Valor inicial)^(1/n) - 1
- Suaviza flutuações anuais para mostrar tendência de longo prazo.

### Growth Rate
- **MoM (Month over Month)**: (Métrica atual - Métrica mês anterior) / Métrica mês anterior.
- **YoY (Year over Year)**: Compara com mesmo período do ano anterior. Elimina sazonalidade.
- **QoQ (Quarter over Quarter)**: Trimestral.

### Regra dos 40 (SaaS)
- Crescimento de receita (%) + Margem EBITDA (%) ≥ 40%.
- Empresas de alto crescimento podem ter margens baixas, desde que a soma supere 40%.

## 7. Análise de Cohort

### Conceito
Agrupa clientes por período de aquisição (cohort) e acompanha comportamento ao longo do tempo.

### Métricas por Cohort
- **Retenção**: % de clientes ativos após 1, 3, 6, 12 meses.
- **Receita por cohort**: MRR gerado por cada safra ao longo do tempo.
- **LTV por cohort**: Valor total gerado por cada safra.

### Interpretação
- **Curva de retenção achatando**: Indica que os clientes restantes são fiéis (bom sinal).
- **Queda contínua**: Problema de product-market fit ou onboarding.
- **Cohorts recentes melhorando**: Produto está evoluindo (bom sinal).
- **Cohorts recentes piorando**: Qualidade da aquisição caindo ou produto deteriorando.

## 8. Análise RFM

### Variáveis
- **Recência (R)**: Quão recentemente o cliente comprou. Quanto mais recente, melhor.
- **Frequência (F)**: Quantas vezes comprou no período. Mais frequente = mais engajado.
- **Monetário (M)**: Quanto gastou total. Maior valor = cliente mais importante.

### Segmentação
| Segmento | R | F | M | Ação |
|----------|---|---|---|------|
| Champions | Alto | Alto | Alto | Programas de fidelidade, early access |
| Leais | Médio-Alto | Alto | Alto | Upsell, cross-sell |
| Potencial | Alto | Baixo | Médio | Nutrição, incentivo à segunda compra |
| Em risco | Baixo | Alto | Alto | Reativação urgente, oferta especial |
| Hibernando | Baixo | Baixo | Baixo | Campanha de win-back ou deprioritizar |

## 9. Pricing (Precificação)

### Estratégias
- **Cost-plus**: Preço = Custo + Margem desejada. Simples mas ignora valor percebido.
- **Value-based**: Preço baseado no valor percebido pelo cliente. Requer pesquisa.
- **Competitiva**: Baseada nos preços de concorrentes. Risco de corrida ao fundo.
- **Dinâmica**: Preços variam por demanda, horário, perfil (ex: Uber surge pricing).
- **Freemium**: Versão gratuita limitada + versão paga. CAC baixo, conversão ~2-5%.

### Elasticidade de Preço
- **Demanda elástica**: Aumento de preço → queda significativa na demanda (luxo, substituíveis).
- **Demanda inelástica**: Aumento de preço → pouca mudança na demanda (essenciais, viciantes).
- **Fórmula**: Elasticidade = % Variação na demanda / % Variação no preço.
  - |E| > 1 = elástica | |E| < 1 = inelástica | |E| = 1 = unitária.

## 10. Working Capital (Capital de Giro)

### Ciclo Operacional
- **PME (Prazo Médio de Estocagem)**: Dias que o estoque fica parado.
- **PMR (Prazo Médio de Recebimento)**: Dias para receber dos clientes.
- **PMP (Prazo Médio de Pagamento)**: Dias para pagar fornecedores.
- **Ciclo de Caixa**: PME + PMR - PMP.
  - Positivo = empresa precisa financiar o giro.
  - Negativo = empresa opera com capital de terceiros (ideal).

### Necessidade de Capital de Giro (NCG)
- **NCG = Ativo operacional circulante - Passivo operacional circulante**.
- Aumento de vendas geralmente aumenta NCG (mais estoque e recebíveis).
- Gestão eficiente: Reduzir PME (giro de estoque), reduzir PMR (cobrança ágil), aumentar PMP (negociar prazos).
