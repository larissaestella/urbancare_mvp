# UrbanFlow — Registro das entrevistas de escopo (protótipo)

Data: 2026-10-22 · Entrevistado: Rafael (Tecnologia/IA) · 8 rodadas.
Fontes lidas: `Downloads/UrbanFlow - Sprint 2 - Business Intelligence e Startup Development.docx` (arquitetura, smoke test, pré-venda, Wizard of Oz, primeiro valor, 2 telas embutidas), `PRODUCT.md`, `DESIGN.md`, `docs/referencias/*` (mockup Figma estático `cELqLax184bs562qqh0Vwh`).

Legenda: **[D]** decisão do usuário · **[R]** padrão recomendado aceito · **[TBD]** em aberto.

---

## 1. Natureza e propósito

| # | Decisão |
|---|---|
| 1.1 | **[D]** Protótipo = **web + backend real com dados, sem MQTT** (evolução do mockup estático do CP2). Sem hardware. |
| 1.2 | **[D]** Serve a quatro momentos: entrega/apresentação à FIAP (Prof. Henio Scheidt), demo técnica de 15 min (Variação B), vídeo de 45 s do Smoke Test (MVP 0) e Wizard of Oz. |
| 1.3 | **[R]** Visual: implementar **fielmente o `DESIGN.md`** ("Placa de Ponto"), não o visual escuro das capturas do docx. |
| 1.4 | **[D]** Stack front: **React + Vite + TypeScript**. |
| 1.5 | **[D]** Backend: **Python (FastAPI)**. |
| 1.6 | **[R]** Banco: **PostgreSQL + TimescaleDB** (série temporal, fiel à arquitetura). |
| 1.7 | **[R]** Execução: **local com Docker Compose** (sem deploy público por ora). |
| 1.8 | **[D]** Prazo: entrega/apresentação ao Prof. Henio **em 4 dias (2026-10-26)**; **Rafael opera a demo**. Ver risco em §7. |
| 1.9 | **[D]** Entregável atual roda **só local, sem nenhum hardware**; tudo que é nuvem/edge/hardware vai para o roadmap. |

## 2. Escopo do MVP (protótipo funcional)

**Telas/módulos [D]:** Operação — Visão geral; Operação — Detalhe do ponto; Operação — Frota; Publicidade — Audiência; Relatórios; Configurações. Mais overlays: Confirmar envio, toasts. Capa não citada (tratar como landing, ver abaixo).

**Landing page B2B do Smoke Test [R]:** no mesmo repositório, **funcional**: CTA principal e Variação B (A/B), formulário de 3 campos (empresa, qtd. linhas/pontos, e-mail corporativo), captura de leads no backend e métricas de conversão.

**Fonte de dados [R]:** **simulador de sensores** envia contagens por HTTP (substitui MQTT) a cada 30 s (com modo acelerado para demo). Sem YOLO real. **Wizard of Oz [D]:** basta o modo de simulação/cenários (sem painel de bastidor); a equipe aciona cenários pré-definidos (ex.: Demo Paulista).

**Seed [R]:** **142 pontos fictícios ancorados em SP** (vias reais, linhas como 875A, 177H, 6450, 7272), sem alegar dado real. Cenário **"Demo"** determinístico que reproduz os números do Figma (1.284 pessoas, 11 min, 7/142 em alerta, 12 extras, Av. Paulista 1578 com 26 pessoas e 17 min) **+ modo livre** de simulação viva.

**Mapa [R]:** estilizado (SVG/canvas) fiel ao `DESIGN.md` (map-ground, formas de status), sem tiles externos.

**Acesso [R]:** login simples com **3 perfis seed**: Operador (Concessionária Via Sul), Gestor OOH (Marca Aurora/agência), Gestão pública. Cada perfil vê seus módulos.

**Despacho [R]:** "Enviar extra" cria **despacho simulado com ciclo de vida**: garagem mais próxima, ETA (ex.: 4 min), estados a caminho → chegou, e a lotação do ponto **cai na simulação**. Critério de pronto: fluxo ponta a ponta **sensor sim → alerta → enviar extra → lotação cai** (D).

**Regra de envio automático [R]:** configurável: o toggle liga a automação (despacha sozinha) ou só sugere; limites editáveis em Configurações. Padrão do docx: lotação > 20 pessoas por > 5 min → alertar a garagem mais próxima e sugerir ônibus extra na linha de maior demanda.

**Tempo de espera [R]:** modelo de fila: lotação ÷ taxa de embarque + headway (estimativa, coerente com contagem anônima; sem rastreio de indivíduos).

**Publicidade [D]:** **apenas números seed ilustrativos** (campanhas, audiência, CPM, exposição fixos, sem derivar dos dados do simulador). Nota: isso contraria o princípio "um sensor, dois compradores" em termos de dados; a derivação fica para o roadmap.

**Relatórios [D]:** **somente pré-visualização na tela + toast** (sem PDF/CSV reais).

**Privacidade [D]:** a API **rejeita qualquer payload fora do schema numérico (< 300 B)**: só ponto, timestamp e contagem; teste automatizado. (Inspetor de payload na UI e schema sem colunas de pessoa não foram escolhidos, mas o schema sem identificadores é consequência natural.)

**Fora do MVP [D]:** MQTT/AWS IoT, hardware (Raspberry Pi 4, câmera 8 MP, YOLOv8n), frota real/GPS, integrações externas, cloud pública.

## 3. Especificação técnica de referência (docx, não implementada no protótipo)

- Edge: Raspberry Pi 4 (4 GB), câmera grande-angular 8 MP, sensor de presença, IP65, Wi-Fi/4G; YOLOv8n local; contagem anônima a cada 30 s; imagens destruídas da memória após a contagem.
- Cloud: MQTT (AWS IoT Core), payload < 300 B, TLS 1.3; banco de séries temporais + motor de regras de lotação.
- Front CCO: mapa de calor, alertas de saturação, gráfico de demanda horária, despacho rápido.
- LGPD: zero imagens salvas, sem reconhecimento facial, dado 100% anônimo.
- Indicadores: latência < 3 s (contagem → tela), precisão > 85 %, modo offline 72 h.

## 4. Validação de negócio (docx)

- **Smoke Test:** 30 decisores (CCO SPTrans, EMTU, privadas) via LinkedIn; landing + vídeo 45 s; headline "Reduza em até 9% os custos de frota ociosa com monitoramento IoT em tempo real"; CTA `QUERO SOLICITAR O PILOTO GRATUITO →`; variação B `AGENDAR DEMONSTRAÇÃO TÉCNICA DO PAINEL CCO (15 MIN) →`; sucesso: conversão ≥ 15 %, ≥ 3 leads completos em 7 dias, > 60 % de aceite de reunião. Prazo 7 dias úteis. Responsáveis: Beatriz e Iago (prospecção), Larissa (landing/métricas), Rafael e Enzzo (demo CCO).
- **Pré-venda:** setup grátis nos 5 primeiros pontos, 60 dias de acesso gratuito + suporte, 30 % de desconto vitalício na assinatura; meta ≥ 5 empresas na lista de espera em 10 dias; sinal forte: ≥ 2 Cartas de Intenção.
- **Wizard of Oz:** alerta manual simulando IA ("Av. Paulista com 28 pessoas aguardando há mais de 6 min. Sugestão: despachar 1 ônibus extra na Linha 875A"); sucesso: ≥ 70 % dos alertas acatados em 5 dias.
- **Primeiro valor:** < 48 h até o primeiro valor; ≥ 1 despacho real baseado no sistema nos 2 primeiros dias. OOH: primeiro relatório auditado (ex.: "Campanha X no Ponto Consolação: 42.800 pessoas impactadas entre 07h e 19h, exposição média 11 min"), justificando anúncio até 25 % mais caro.

## 5. Roadmap da solução completa

Todas as fases abaixo estão no roadmap (**[D]**); a ordem foi **confirmada [D]** na rodada 8.

1. **Protótipo** (esta entrega): web + backend + simulador.
2. **Piloto real:** edge real (Raspberry Pi + YOLOv8n) + AWS IoT/MQTT em 3–5 pontos; valida precisão > 85 %, latência < 3 s, offline 72 h. Hardware **próprio**; câmeras parceiras (CET/concessionárias) são alternativa futura. A pergunta sobre hardware foi respondida "desnecessário no MVP" e depois situada no piloto posterior (D).
3. **Frota real:** GPS/AVL (ex.: SPTrans Olho Vivo), despacho e ETA reais.
4. **Publicidade auditável:** métricas derivadas dos dados, comprovação auditada, integração com plataformas OOH.
5. **Previsão de demanda com ML + SaaS multi-concessionária** (única fase marcada explicitamente como prioridade pelo usuário; a posição na ordem acima está em aberto).

**Modelo de negócio [D]:** **setup por ponto + assinatura mensal por ponto**. Valores **[TBD]** (confirmado na rodada 8: definir após o smoke test; não inventar). Condições já definidas: pré-venda do §4.

## 6. Questões levantadas e pontos sensíveis

- **Inconsistência de números entre fontes:** regra automática (> 20 pessoas / > 5 min) vs. exemplo Wizard of Oz (28 pessoas / > 6 min) vs. primeiro valor (26 pessoas / > 5 min) vs. Figma (26 pessoas / 17 min). Consistentes com o gatilho, mas o cenário "Demo" deve fixar um valor único por tela.
- **"9 %":** no docx é "custos de frota ociosa"; no Figma é "km rodado ocioso". Manter o texto do Figma na tela (copy verbatim, PRODUCT.md) e o do docx na landing.
- **Wizard of Oz:** resolvido na rodada 8: usa o modo de simulação/cenários, sem painel de injeção manual.
- **PRODUCT.md** cita "câmeras parceiras já instaladas"; o docx especifica hardware próprio. Resolvido para o roadmap (§5); atualizar PRODUCT.md quando o protótipo começar.
- **Princípio "um sensor, dois compradores"** fica parcial no MVP por Publicidade ser seed.
- Dados sempre rotulados "Dados ilustrativos — mockup estático para validação (CheckPoint 2)" (ajustar o texto: não é mais estático).

## 7. Riscos e pendências

- **Escopo vs. prazo:** 6 telas + landing + backend + simulador + despacho + auth em 4 dias é ambicioso. **Inegociáveis [D]:** (1) Visão geral com fluxo ponta a ponta e (2) landing + leads do smoke test. O restante cai de baixo para cima nesta ordem: Detalhe do ponto, Publicidade (seed), Frota, Relatórios/Configurações com regra editável, login por perfil (o login é o primeiro a ser cortado; cair para seletor de perfil ou nenhum).
- **[TBD]** apenas os valores de preço (após o smoke test). Ordem do roadmap, data e Wizard of Oz foram fechados na rodada 8.

## 8. Consequências registradas (pós-plano)

- A landing do smoke test roda **só local** nesta entrega; ela demonstra o mecanismo (A/B, 3 campos, captura de leads), mas **não** recebe tráfego real do LinkedIn. Deploy público é roadmap.
- Plano de implementação: `docs/PLANO.md` (aguardando aprovação).
