# Guia de Tributação Brasileira para Análise de Dados

## 1. Visão Geral do Sistema Tributário Brasileiro

O Brasil possui um dos sistemas tributários mais complexos do mundo, com tributos nas esferas federal, estadual e municipal. Para análise de dados de negócio, é essencial compreender os principais impostos e como impactam as operações.

### Esferas Tributárias

| Esfera | Principais Tributos |
|--------|-------------------|
| Federal | IRPJ, CSLL, PIS, COFINS, IPI, IOF, IRRF |
| Estadual | ICMS, IPVA, ITCMD |
| Municipal | ISS, IPTU, ITBI |

## 2. ICMS — Imposto sobre Circulação de Mercadorias e Serviços

### Conceito
Principal imposto estadual, incide sobre circulação de mercadorias, transporte interestadual/intermunicipal e comunicação.

### Alíquotas Internas (Principais Estados)
- **São Paulo**: 18% (alíquota padrão)
- **Rio de Janeiro**: 20% (após FECP)
- **Minas Gerais**: 18%
- **Paraná**: 19.5% (após Fundo Estadual)
- **Rio Grande do Sul**: 17%
- **Demais estados**: Variam entre 17% e 20%

### Alíquotas Interestaduais
- **Sul e Sudeste (exceto ES) → Norte, Nordeste, CO e ES**: 7%
- **Demais operações interestaduais**: 12%
- **Importados (Resolução 13/2012)**: 4%

### ICMS-ST (Substituição Tributária)
Regime em que a responsabilidade do recolhimento é atribuída a um contribuinte diferente do que realizou o fato gerador.
- **MVA (Margem de Valor Agregado)**: Percentual adicionado à base de cálculo para antecipar o ICMS das etapas seguintes.
- **Base de cálculo ST**: (Preço de venda + frete + IPI) × (1 + MVA%)
- **Impacto no caixa**: Antecipação de imposto afeta o fluxo de caixa das empresas.

### DIFAL (Diferencial de Alíquota)
- Cobrado nas vendas interestaduais ao consumidor final não contribuinte.
- **Cálculo**: Alíquota interna do estado destino - Alíquota interestadual.
- **Partilha**: 100% para o estado de destino.

### Créditos de ICMS
- Sistema de débito/crédito: ICMS pago na compra gera crédito para abater do ICMS da venda.
- **Vedação de crédito**: Material de uso/consumo (até regulamentação), energia elétrica (exceto indústria).
- **Estorno de crédito**: Obrigatório quando mercadoria é destinada a operação isenta/não tributada.

## 3. PIS e COFINS

### Regime Cumulativo (Lucro Presumido)
- **PIS**: 0.65% sobre faturamento bruto
- **COFINS**: 3.00% sobre faturamento bruto
- Sem direito a créditos. Base de cálculo simples.

### Regime Não Cumulativo (Lucro Real)
- **PIS**: 1.65% sobre faturamento bruto
- **COFINS**: 7.60% sobre faturamento bruto
- **Com créditos** sobre: compras de mercadorias, insumos, energia elétrica, aluguéis, depreciação de ativos.
- **Carga efetiva típica**: 3-5% após créditos (varia por setor).

### Monofásico
- Tributação concentrada em uma única fase (fabricante ou importador).
- Alíquotas diferenciadas (geralmente mais altas).
- Fases subsequentes com alíquota zero.
- **Setores**: Combustíveis, medicamentos, cosméticos, veículos, autopeças.

### PIS/COFINS na Importação
- **PIS-Importação**: 2.10%
- **COFINS-Importação**: 9.65% (+ adicional de 1% para alguns produtos)
- Base: Valor aduaneiro + ICMS + PIS/COFINS-Importação (cálculo "por dentro").

## 4. IPI — Imposto sobre Produtos Industrializados

### Conceito
Imposto federal sobre produtos industrializados, seletivo conforme essencialidade do produto.
- **TIPI (Tabela)**: Cada produto tem uma alíquota na tabela.
- **Alíquotas**: De 0% (alimentos básicos) a 300%+ (cigarros).
- **Crédito**: IPI na compra de insumos gera crédito (sistema débito/crédito).
- **Base de cálculo**: Preço de venda (saída da indústria).

## 5. ISS — Imposto sobre Serviços

### Conceito
Imposto municipal sobre prestação de serviços (exceto os tributados por ICMS).
- **Alíquota mínima**: 2%
- **Alíquota máxima**: 5%
- **Lista de serviços**: LC 116/2003 (203 serviços listados).
- **Local de incidência**: Em regra, município do estabelecimento do prestador.
  - **Exceções**: Construção civil (local da obra), leasing (domicílio do tomador).

## 6. IRPJ e CSLL — Tributos sobre o Lucro

### Lucro Presumido
Para empresas com faturamento anual ≤ R$ 78 milhões.
- **Presunção de lucro** (base IRPJ):
  - 8% para comércio e indústria
  - 32% para serviços
  - 1.6% para revenda de combustíveis
- **IRPJ**: 15% sobre lucro presumido + 10% sobre excedente de R$ 60.000/trimestre.
- **CSLL**: 9% sobre base presumida (12% comércio, 32% serviços).

### Lucro Real
Obrigatório para empresas com faturamento > R$ 78 milhões/ano.
- **IRPJ**: 15% sobre lucro líquido ajustado + 10% sobre excedente de R$ 20.000/mês.
- **CSLL**: 9% sobre lucro líquido ajustado.
- **Adições e exclusões**: Despesas indedutíveis adicionadas; incentivos fiscais excluídos.
- **Prejuízo fiscal**: Compensável em até 30% do lucro de períodos futuros.

### Simples Nacional
Regime simplificado para micro e pequenas empresas (faturamento ≤ R$ 4.8 milhões/ano).
- Alíquota única incidente sobre faturamento (inclui IRPJ, CSLL, PIS, COFINS, IPI, ICMS, ISS, CPP).
- **Anexos I-V**: Alíquotas variam por atividade e faixa de faturamento.
- **Faixa inicial**: ~4% (comércio) a ~15.5% (serviços profissionais).
- **Faixa máxima**: ~19% (comércio) a ~33% (serviços profissionais).

## 7. Calendário Fiscal

### Obrigações Mensais
| Obrigação | Prazo | Descrição |
|-----------|-------|-----------|
| DCTF (Web) | Até dia 15 do mês seguinte | Declaração de débitos e créditos federais |
| EFD-ICMS/IPI (SPED Fiscal) | Varia por estado (dia 15-25) | Escrituração Fiscal Digital |
| EFD-Contribuições | 10º dia útil do 2º mês seguinte | PIS/COFINS escrituração |
| GIA | Varia por estado | Guia de Informação e Apuração do ICMS |
| PGDAS-D (Simples) | Dia 20 do mês seguinte | Cálculo Simples Nacional |

### Obrigações Anuais
| Obrigação | Prazo | Descrição |
|-----------|-------|-----------|
| ECF | Último dia útil de julho | Escrituração Contábil Fiscal |
| ECD | Último dia útil de maio | Escrituração Contábil Digital |
| DIRF | Último dia útil de fevereiro | Declaração do IR Retido na Fonte |
| DEFIS (Simples) | 31 de março | Declaração do Simples Nacional |

## 8. Nota Fiscal Eletrônica (NF-e)

### Tipos
- **NF-e (modelo 55)**: Mercadorias (venda, transferência, devolução, remessa).
- **NFS-e**: Serviços (emitida no portal do município).
- **NFC-e (modelo 65)**: Consumidor final (varejo).
- **CT-e**: Transporte de cargas.
- **MDF-e**: Manifesto de documentos fiscais.

### Campos Essenciais para Análise
- **CFOP**: Código Fiscal de Operação — indica natureza da operação.
  - 5xxx: Operações internas (mesmo estado).
  - 6xxx: Operações interestaduais.
  - 7xxx: Exportações.
  - 1xxx/2xxx/3xxx: Entradas correspondentes.
- **NCM**: Classificação do produto (8 dígitos, determina alíquotas IPI e ICMS-ST).
- **CST/CSOSN**: Código de Situação Tributária (determina regime de tributação da operação).

### CFOPs mais comuns
| CFOP | Descrição |
|------|-----------|
| 5102/6102 | Venda de mercadoria adquirida |
| 5101/6101 | Venda de produção própria |
| 5202/6202 | Devolução de compra |
| 5405/6404 | Venda com ST já recolhido |
| 5910/6910 | Remessa em bonificação |
| 5949/6949 | Outra saída não especificada |

## 9. Reforma Tributária (EC 132/2023)

### Novos Tributos (fase de transição 2026-2033)
- **IBS (Imposto sobre Bens e Serviços)**: Substitui ICMS + ISS. Estadual + municipal.
- **CBS (Contribuição sobre Bens e Serviços)**: Substitui PIS + COFINS. Federal.
- **IS (Imposto Seletivo)**: Sobre bens prejudiciais à saúde/meio ambiente ("imposto do pecado").

### Características do IBS + CBS
- **IVA Dual**: Um IVA federal (CBS) e um IVA subnacional (IBS).
- **Não cumulativo amplo**: Crédito integral de todos os bens e serviços adquiridos.
- **Destino**: Imposto recolhido no local do consumo, não da produção.
- **Alíquota de referência estimada**: ~26.5% (CBS ~8.8% + IBS ~17.7%).
- **Cashback para famílias de baixa renda**: Devolução de parte do imposto.

### Cronograma de Transição
- **2026**: Início CBS (0.9%) + IBS (0.1%) como teste.
- **2027**: CBS integral. Extinção PIS/COFINS.
- **2029-2032**: Redução gradual ICMS + ISS, aumento IBS.
- **2033**: Extinção total ICMS + ISS. IBS em vigor pleno.

## 10. Análise Tributária em Dados de Negócio

### Indicadores Relevantes
- **Carga tributária efetiva**: Total de impostos / Receita bruta.
- **Tax rate efetivo**: (IRPJ + CSLL) / Lucro antes IR.
- **Crédito tributário acumulado**: Saldo de ICMS/PIS/COFINS a recuperar.
- **Impacto ST no caixa**: MVA paga antecipadamente vs. margem real.

### Red Flags em Dados Fiscais
- Alíquota efetiva de PIS/COFINS muito abaixo de 3.65% (cumulativo) sem justificativa.
- CFOP de transferência (5152/6152) com preço muito divergente do mercado.
- NCM incorreto levando a tributação indevida de IPI ou ICMS-ST.
- Crédito de ICMS sobre itens que não dão direito a crédito.

### Oportunidades de Otimização (Legais)
- Revisão de NCM para produtos com alíquota menor.
- Aproveitamento de créditos presumidos estaduais.
- Análise de benefício fiscal por operação (isenção, diferimento, suspensão).
- Planejamento logístico: rotas interestaduais com menor carga tributária.
