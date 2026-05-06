Recommended Flow Redesign
Landing (v2)

HERO
├── Headline: "Pare de ser o gargalo da sua empresa." [keep]
├── Sub: "Seu escritório virtual com IA. Agentes sugerem. Você decide." [keep]
├── Primary CTA: "Escolha seu setor e veja em 60s" → scrolls to demo [CHANGE]
└── Secondary CTA: "Montar meu escritório" → /onboarding [keep as secondary]

PERSONA SELECTOR [NEW]
├── Tile: Distribuidora / Atacado
├── Tile: Consultoria / Serviços
├── Tile: Varejo / E-commerce
└── (Pre-selects demo context below)

INTERACTIVE DEMO [UPDATE]
├── Chip questions swap per persona selection
├── Answers are sector-specific
└── After first answer: CTA "Ver isso com os meus dados" → /onboarding

HOW IT WORKS [keep, minor copy tune]
AGENT GRID [keep]
HITL CARD [keep]
SOCIAL PROOF [keep — add urgency if more cases available]
FAQ [keep]
FINAL CTA [keep]
Onboarding (v2)

Step 0 — Persona (pre-auth, 0 friction)
URL: /onboarding
Content: Which industry are you in? (3 big tiles, same as landing)
If user came from landing persona selection → pre-fill and skip

Step 1 — Conversational "Meet Your Team" (pre-auth)
URL: /onboarding/meet
Blu: "Oi! Vou coordenar seu time de IA. Como se chama sua empresa?"
Blu: "Ótimo. Seu maior problema hoje: fluxo de caixa, estoque ou atendimento?"
Blu: "Último: você toca isso sozinho ou tem time?"
(3 bubbles, each with 3 multiple-choice chips + free text option)

Step 2 — Demo Dashboard (pre-auth, the "aha moment")
URL: /onboarding/preview
Show: Simulated dashboard for their persona + pain point
Visible: 2-3 insights + 2 pending approvals
Blurred: "Strategist pode prever os próximos 30 dias" (hover: upgrade teaser)
CTA: "Quero isso com os meus dados" → triggers auth

Step 3 — Auth (Google OAuth only, prominent) [SIMPLIFY]
URL: /onboarding/auth
Remove email/password — Google-only reduces friction
(Re-add email option later once Google conversion is measured)

Step 4 — Data Connection [keep DataFork, rename/polish]
URL: /onboarding/data

Step 5 — Agent Activation [keep, pre-select based on conversational answers]
URL: /onboarding/agents

Step 6 — First Approval Moment [NEW]
URL: /onboarding/approval
Surface 1 simulated agent proposal matching their vertical
Let user tap Aprovar / Editar / Recusar
"Blu anotou. Vou sugerir algo parecido na próxima semana."
This IS the activation event.

Step 7 — LaunchPad [update]
Remove PackageProposal from wizard entirely
Replace summary with: Agents activated + checklist + next steps
Blurred premium insight = contextual freemium hook
CTA: "Entrar no Centro de Comando"
Experiment Backlog (Prioritized)

# Experiment Metric Priority

1 Persona selector on landing before demo Time-to-demo-click, landing→signup High
2 Move auth to step 3 (post-conversation) Landing→signup rate High
3 Conversational flow vs. BusinessDNA form Onboarding completion High
4 Insert demo dashboard (aha moment) pre-auth % reaching auth step High
5 First approval moment in onboarding First-approval rate High
6 Google-only auth vs. Google+email Auth completion rate Medium
7 Remove PackageProposal from wizard Onboarding completion Medium
8 Blurred premium features in LaunchPad Free-to-paid conversion Medium
9 Persona-aware chip responses in demo Demo engagement rate Medium
10 Email sequence: 24h no-data-connected trigger Day-7 activation Low
Anti-Patterns to Eliminate
Auth.tsx email/password as default — adds form fields before any value. Remove from initial path.
BusinessDNA.tsx dropdown for vertical before the user has seen a personalized preview — pre-fill from conversational answers instead.
PackageProposal inside the wizard — pricing before value destroys momentum.
Static demo chips — a services company sees distribuidora data. Fix with persona context.
LaunchPad spinner with no "preview" content — users stare at a loading state. Show the first approval simulation during bootstrap.
Files to Modify
File Change
LandingPage.tsx Add persona selector tiles, make demo chip content persona-conditional, update primary CTA flow
Auth.tsx Remove as onboarding entry; reposition as step 3; simplify to Google-only initially
Welcome.tsx Replace with Persona step (3-tile selector)
BusinessDNA.tsx Replace 4-field form with 3-bubble conversational flow
New: steps/ConversationalMeet.tsx 3-question conversational UI with Blu avatar
New: steps/DemoDashboard.tsx Persona-matched simulated dashboard with blurred premium features
New: steps/FirstApproval.tsx Simulated agent proposal + Aprovar/Editar/Recusar buttons
LaunchPad.tsx Add blurred premium teaser, remove PackageProposal dependency
state.ts Add persona field, painPoint field, firstApprovalDecision field
