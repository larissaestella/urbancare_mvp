# Product

## Platform

web

## Stack

Figma only (médium-fidelity static mockup). Deliverable lives in Figma file `cELqLax184bs562qqh0Vwh`; frames are redrawn in place. No code.

## Users

- **Concessionária operators** (e.g. "Concessionária Via Sul", 142 monitored stops): watch stop crowding and wait times live, decide when to dispatch extra buses from a garage.
- **OOH advertising managers** (38 panels in bus stops): price ad slots by audience and prove campaign reach to brands (e.g. "Marca Aurora").
- **Gestão pública (secondary):** SLA monitoring of transit service quality for fiscalização.
- **Primary evaluator of this artifact:** professors grading the FIAP 4ESPS "BI e Startup Development" CheckPoint 2; secondary: 7 usability-test participants (5 passengers + 2 managers, 31/08–04/09).

## Product Purpose

Bus concessionaires and ad companies decide on estimates, with no real-time data on people flow, wait time, or engagement at bus stops. UrbanFlow counts people anonymously via partner cameras already installed at stops, processed at the edge, and turns that into operational decisions (extra buses) and ad-audience proof (CPM, exposure time).

Success for this artifact: reads as a credible, realistic product; test goal ≥ 6/7 approve, ≥ 80% understand unaided, mean utility score ≥ 8.

Team (FIAP 4ESPS): Beatriz (Negócios/BI), Enzzo (Infra/IoT), Iago (Testes), Larissa (Protótipo/UX-UI), Rafael (Tecnologia/IA). Hypotheses: H1 static mockup suffices to explain value; H2 users understand camera monitoring unaided and rate utility ≥ 8; H3 real-time data drives fleet dispatch and ad pricing. Reported test mean: 8,7/10.

## Positioning

One sensor (the stop camera) serves two buyers: dwell time at the stop is simultaneously a wait-time KPI for the operator and an exposure-time KPI for the advertiser.

## Operating Context

Screens: 00 Capa · 01 Operação — Visão geral · 02 Operação — Detalhe do ponto · 03 Publicidade — Audiência · 04 Operação — Frota · 05 Relatórios · 06 Configurações (04–06 added 2026-09-27 at user request, outside the test script; content illustrative, derived from CP2 value props. 06 is a single scrollable column of collapsible sections — Conta, Aparência, Idioma e região, Regra de envio automático, Segurança, Sobre — plus a static logout block; only section headers are interactive, per user) · overlays: Confirmar envio dialog, Toast ônibus enviado, Toast relatório. Test script maps screens to hypotheses H2 (understanding/utility), H3 (fleet decision, pricing and reach proof).

## Capabilities and Constraints

- All copy and numbers are fixed and must be preserved verbatim (user-confirmed).
- Mockup is static; all data is illustrative and labeled "Dados ilustrativos — mockup estático para validação (CheckPoint 2)".
- Not in prototype: IoT hardware, real image processing, external integrations, interactivity.
- Terminology: ponto, linha, garagem, lotação, espera, painel, CPM, audiência qualificada, comprovação de campanha.

## Brand Commitments

Name "UrbanFlow". No other visual commitment (logo color and dark theme explicitly left open).

## Evidence on Hand

Source docs: `~/Downloads/CheckPoint 1 - BI 1.pdf`, `~/Downloads/CheckPoint 2 - BI - Definição do Protótipo.pdf`. Only the illustrative figures in the Figma file. No real customers, pricing, or benchmarks exist; do not invent any.

## Product Principles

1. Privacy is visible: "Contagem anônima — nenhuma imagem é armazenada" is part of the product, not a footnote.
2. Every number leads to a decision (send bus, price slot, prove campaign).
3. Live state first, history second.
4. One sensor, two audiences — shared vocabulary across Operação and Publicidade.

## Accessibility & Inclusion

Status colors (normal/atenção/crítico) must never rely on hue alone; text contrast WCAG AA.
