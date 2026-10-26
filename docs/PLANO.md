# UrbanFlow — Plano de implementação do protótipo

Base: `docs/ENTREVISTAS.md` (decisões D/R). Hoje: 2026-10-22. Entrega ao Prof. Henio: **2026-10-26** (Rafael opera a demo). Status: **plano aprovado; Fatia 0 concluída em 2026-10-22** (`docker compose up`, `scripts/check_fatia0.py`, 20 testes pytest). Próximo: Fatia 1. Desvios da Fatia 0: psycopg direto (sem SQLAlchemy); schema por `CREATE IF NOT EXISTS` no start da API (mudança de coluna exige `docker compose down -v`); banco publicado em 55432 (5432 ocupada no host); salto do relógio para trás = reinício de cenário (`reset_scenario` em `main.py`, ponto de encaixe do seed Demo); SSE e `/stream` ficam para a Fatia 1. **Fatia 1 concluída em 2026-10-25** (`check_fatia1.py`, `check_fatia1_ui.py`, 25 testes). Desvios da Fatia 1: `/stream` envia um único evento `snapshot` por segundo (KPIs, lista, mapa, gráfico, relógio) em vez de eventos separados; só `hourly_network` (sem `hourly_stop`, que é do Detalhe); toggle da regra automática só exibe (a regra sugere, o operador envia); controles do relógio em `/bastidor`; corrigidos deadlock no reset do Demo e leitura antiga sobrescrevendo a lotação. Atrasado 1 dia: em 25/10 a Fatia 2 entra na sequência e a Fatia 3 só se sobrar tempo. **Fatia 2 concluída em 2026-10-25** (`check_fatia2.py`, `check_fatia2_ui.py`, 32 testes): `/landing` (variante sorteada e fixa por navegador, `?v=A|B` força), `/landing/metricas` (conversão = cliques ÷ visitas por variante vs. 15 %; leads vs. 3), zerar métricas no `/bastidor`. Visita e clique contam uma vez por visitante e variante; um lead por visitante e variante; e-mail de provedor gratuito é recusado; sem IP nem user agent. O cenário Demo não apaga leads. **Fatia 3, item 1 (Detalhe do ponto) concluído em 2026-10-25** (`check_fatia3_ui.py`): `/pontos/SP-0412`, só frontend. Ao vivo: lotação, espera, status, extra a caminho e o envio pela recomendação (mesmo diálogo da Visão geral). Verbatim do render, sem modelo: linhas 875A/177H/6450 (o seed só liga a 875A), permanência 18/34/27/14/7 %, curva 14h–18h30 (o último ponto é ao vivo), próximo ônibus 875A · 6 min · 82 % (repete a cada 12 min de sim) e a cena da detecção (só a contagem e o horário são ao vivo). Semanal/Mensal mostram aviso de que entram com os dados do piloto. §8 aplicado: "Sensor SP-0412 (simulado)" no cabeçalho e no rótulo da cena; relógio de sim no lugar da data. **Fatia 3, item 2 (Publicidade) concluído em 2026-10-26** (`check_fatia3_publicidade_ui.py`): `/publicidade`, só frontend e todo verbatim do render 03 (KPIs, mapa de calor, ranking, campanha Marca Aurora, comparação). Diária/Mensal e os botões Exportar, Gerar relatório auditado (PDF), Compartilhar e Ver todos não geram nada: avisam que entram com os dados do piloto. §8.1 aplicado no rodapé. Datas de calendário do render (24/08–30/08, 17/08–13/09) mantidas verbatim. **Fatia 3, item 4 (Configurações) implementado em 2026-10-26** (`check_fatia3_config_ui.py`): `/configuracoes`, só frontend, verbatim do Figma 06 (nó 32:112). Seções colapsáveis (Conta e Aparência abertas); toggles e segmentados só no estado da tela; nada é gravado (a regra da simulação segue fixa em > 20 por 5 min para não descalibrar o Demo); botões de conta avisam que entram com o login real. Seção Sobre alinhada a §8.1 ("Protótipo Sprint 2 · simulação"). Login real: não existe no Figma, fica de fora.

## 1. Princípios do plano

1. **Relógio de simulação é a base.** O backend tem um único relógio de sim com multiplicador (1× ao vivo; ~20–30× para demo/vídeo). Simulador, regra (>20 por >5 min), ciclo do despacho (a caminho → chegou) e queda de lotação rodam em **tempo de sim**, nunca em relógio de parede. Entra na fatia 0.
2. **Cenário Demo é seed calibrado, não emergente.** Os números do render são reproduzidos exatamente; o modo livre é a simulação viva.
3. **Fidelidade ao render alvo.** A referência visual são os renders da Placa de Ponto (`docs/referencias/*.png`), não as capturas escuras do docx. Textos e números são verbatim (PRODUCT.md).
4. **Primeiro o inegociável:** Visão geral com fluxo ponta a ponta e landing + leads. O resto cai de baixo para cima (§6).
5. **"Pronto" é checagem automática** (§7), não impressão.

## 2. Arquitetura (local, Docker Compose, sem hardware)

```
urbanflow/
  docker-compose.yml        timescaledb · api · sim · web
  apps/api/                 FastAPI, SQLAlchemy/psycopg, Pydantic v2, pytest
  apps/sim/                 simulador (container separado, chama a API por HTTP)
  apps/web/                 React + Vite + TypeScript
  docs/                     ENTREVISTAS.md, PLANO.md
```

- **Ingestão:** `POST /ingest/readings` por ponto, modelo Pydantic com `extra="forbid"` (só `stop_id`, `ts`, `count`) e checagem de corpo ≤ 300 B. Qualquer outro campo ou corpo maior → 422/413. Não existe coluna de imagem ou identificador de pessoa no schema.
- **Relógio:** `GET/POST /sim/clock` (multiplicador, pausa, salto para o cenário). O `sim` consulta o relógio e emite uma leitura por ponto a cada 30 s de sim. Teto de 30× para não passar de ~140 req/s locais (142 pontos por tick); se o teto doer, batch interno acima disso (decidir na fatia 0 medindo).
- **Tempo real no front:** **SSE** (`/stream`) com eventos de leitura agregada, alerta, despacho e relógio; fallback para polling de 2 s se SSE der problema. Decidido; não reabrir.
- **Banco (TimescaleDB):** `stops` (com `svg_x`, `svg_y` para o mapa estilizado), `lines`, `stop_lines`, `garages`, `readings` (hypertable), `hourly_network` e `hourly_stop` (histórico pré-gerado em granularidade horária, 4 semanas; **não** gerar linhas de 30 s para 4 semanas, ≈ 11 M linhas), `alerts`, `dispatches`, `leads`, `events` (A/B e conversão), `settings`, `users` (perfis seed).
- **Fila / espera:** por ponto, `espera = lotação ÷ taxa_de_embarque` com `headway` por linha; parâmetros por ponto calibrados no seed.
- **Dinâmica do simulador:** chegadas por ponto seguem a curva horária; ônibus regulares embarcam pela taxa; despacho extra, ao chegar, embarca até N pessoas de uma vez (lotação cai).
- **Perfis:** seletor de perfil primeiro (Operador Via Sul, Gestor OOH, Gestão pública); login real só se sobrar tempo.

## 3. Seed calibrado do cenário Demo (alvos exatos)

| Alvo (render) | Como é garantido |
|---|---|
| 1.284 pessoas nos pontos agora | contagens por ponto semeadas somam exatamente 1.284 às 18:42 |
| 11 min espera média, +3 acima da meta 8 | taxas de embarque calibradas para a média ponderada fechar 11 |
| 7/142 em alerta (3 críticos, 4 atenção) | 3 pontos > 20 por > 5 min; 4 pontos entre faixa de atenção e 20 |
| Av. Paulista, 1578: 26 pessoas, 17 min, linha 875A | taxa do ponto = 26/17 pessoas/min |
| Terminal Sto. Amaro Pl. 3: 24 pessoas, 6450 | espera conforme o render atual (15 min), não a captura do docx (16) |
| R. da Consolação, 900: 22 pessoas, 14 min, 177H, "EXTRA A CAMINHO" | despacho já em curso no seed |
| Av. Rebouças, 1200: 18 pessoas, 12 min, 7272, "ATENÇÃO" | idem |
| 12 extras hoje, -9% km ocioso, 4 min ganho | contadores semeados; os 12 incluem despachos pré-existentes e o contador sobe ao enviar |
| +18% vs. média do horário | média das 4 semanas pré-gerada para 18h |
| Barras 05h–22h, previsão de 19h em diante | `hourly_network`; previsão = média das 4 semanas (ML é roadmap) |
| Mapa | apenas o recorte Paulista/Consolação/Rebouças com ~15 marcadores em `svg_x/svg_y`; 142 é o total de rede. Sem projeção geográfica |

Relógio do cenário abre em "Seg 18:42". Detalhe do ponto (SP-0412): faixas de permanência 18/34/27/14/7 % e curva de lotação com limite 20, também semeadas.

## 4. Fatias por dia

**Quinta 22 (noite) + sexta 23: Fatia 0, fundação**
- Compose (timescaledb, api, sim, web), schema + migrações, seed base de 142 pontos, linhas, garagens.
- Ingest com validação estrita e teste de rejeição.
- Relógio de sim, simulador, regra engine em tempo de sim, ciclo do despacho.
- `DESIGN.md` como variáveis CSS + primitivas: placa (plate), faixa de título, pill de status com forma (círculo/triângulo/quadrado), chip de linha, botões, toggle, segmentado, KPI strip, sidebar totem. Fontes Barlow e Barlow Semi Condensed.
- Saída: `docker compose up` sobe tudo, leituras fluem, alerta nasce após 5 min de sim.

**Sábado 24: Fatia 1, Visão geral ponta a ponta (inegociável)**
- Título + KPI strip ao vivo, mapa SVG estilizado com tooltip, lista de pontos em alerta, gráfico horário (SVG manual, para casar com o DESIGN), regra de envio automático (toggle + SE/ENTÃO + 12 disparos / -9% / 4 min), selo "Contagem anônima".
- Diálogo "Confirmar envio" → despacho → toast "ônibus enviado" → lotação cai na simulação. Regra auto: sugerir ou despachar sozinha.
- Cenário Demo reproduzível com um clique + modo livre; controles discretos de relógio (modo bastidor, fora da UI de produto).
- Saída: fluxo "sensor sim → alerta → enviar extra → lotação cai" passa no script de aceitação.

**Domingo 25 (manhã): Fatia 2, landing e leads (inegociável)**
- Landing B2B: headline/subheadline/CTA/microcopy exatos do docx, atribuição A/B (A: `QUERO SOLICITAR O PILOTO GRATUITO →`; B: `AGENDAR DEMONSTRAÇÃO TÉCNICA DO PAINEL CCO (15 MIN) →`), formulário de 3 campos, `leads` + `events`, vista simples de conversão (visitas, cliques, leads, % vs. meta de 15 %).
- Espaço para o vídeo de 45 s (embed placeholder; o vídeo é gravado depois com o cenário Demo).
- Nota: **a landing é local** e não recebe tráfego real do LinkedIn; demonstra o mecanismo. Deploy público é roadmap.

**Domingo 25 (tarde): Fatia 3, extras em ordem de corte**
1. Detalhe do ponto (SP-0412). 2. Publicidade (seed, como no render 03). 3. Frota (**puxar texto do Figma ao iniciar a fatia**; não inventar). 4. Relatórios (preview + toast) e Configurações (regra editável; texto do Figma). 5. Login real.

**Segunda 26 (manhã): buffer + ensaio**
- Rodar a checagem de aceitação, ensaiar a demo de 15 min e o vídeo de 45 s, `git init` + tag do estado bom conhecido (perguntar antes de commitar).

## 5. Telas: fonte do conteúdo

| Tela | Fonte | Observação |
|---|---|---|
| 01 Visão geral, 02 Detalhe, 03 Publicidade, overlay Confirmar | renders `docs/referencias/*.png` | verbatim |
| 00 Capa | render `00-capa.png` | decidir se vira cabeçalho da landing |
| 04 Frota, 05 Relatórios, 06 Configurações | **Figma `cELqLax184bs562qqh0Vwh`** | só existem lá; ler quando a fatia começar |
| Landing | docx Sprint 2 | copy verbatim; layout em Placa de Ponto |

## 6. Ordem de corte (do primeiro a sair)

Login real → Configurações → Relatórios → Frota → Publicidade → Detalhe do ponto. **Nunca cortar:** Visão geral ponta a ponta e landing + leads.

## 7. Critérios de pronto (automatizados)

- **pytest:** payload com campo extra rejeitado; corpo > 300 B rejeitado; regra `>20 por >5 min` em tempo de sim (dispara em 5 min de sim, não antes; reseta se cair); ciclo do despacho (criado → a caminho → chegou) e queda de lotação.
- **Script e2e do cenário Demo:** carrega o seed, confere 1.284 / 11 min / 7 em alerta / Paulista 26 e 17 min, dispara o despacho, avança o relógio e verifica queda de lotação e contador de extras +1.
- **Checagem visual manual** contra os renders (lado a lado) para as telas implementadas.

## 8. Decisões a aprovar junto com este plano

1. **Rótulo de dados.** O texto "Dados ilustrativos — mockup estático para validação (CheckPoint 2)" ficou errado (não é mais estático; agora é a Sprint 2). Proposta: **"Dados ilustrativos — simulação para validação (Sprint 2)"**.
2. **"Câmera parceira CAM-0412 (já instalada na via)"** no cabeçalho do Detalhe contradiz o docx (hardware próprio, Raspberry Pi). Proposta: trocar por **"Sensor SP-0412 (simulado)"**. Alternativa: manter verbatim.
3. **Data do cabeçalho "Seg, 31/08 · 18:42":** proposta de mostrar o relógio de simulação (abre em "Seg 18:42"), sem data de calendário fixa.
4. **ETA do despacho:** render e diálogo mostram **9 min** (Garagem Vila Mariana); o docx diz **4 min**. Proposta: manter **9 min** do render (o "4 min" é "ganho médio de espera").
5. **Controles do relógio de simulação** (pausa, multiplicador, saltar para cenário) em um modo bastidor discreto, fora das telas de produto, que serve também ao Wizard of Oz.
6. **Profundidade além dos renders (pedido do Rafael, 26/10).** Visões e ações que não existem nos renders nem no Figma passam a existir com **dados ilustrativos derivados dos números verbatim**, nunca soltos: Publicidade Diária = fatia da semana pela coluna do mapa de calor (os 7 dias somam 412 mil), Mensal = 4 semanas de agosto (a última é a do render; a anterior = 412 ÷ 1,12); Detalhe Semanal/Mensal = picos da 875A com minutos acima do limite (a semana soma 162 min, que é a última barra do mês). Relatórios geram PDF de verdade pela impressão do navegador (`/relatorios/ver?tipo=diario|semanal|mensal|campanha`, seções = "Conteúdo dos relatórios" do Figma 05); "Gerar relatório" escolhe tipo e destinatário e acrescenta a linha; Exportar da Publicidade baixa CSV. Lista `/pontos` (os 142 ao vivo pelo `GET /stops`, que ganhou linha, extra a caminho, espera e status sem mudar o schema), Monitorar (guardado no navegador), "Ver todos" e clique no mapa (SP-0412 abre o Detalhe; os demais, a lista filtrada); Publicidade "Ver todos" lista os 38 painéis somando 412 mil. Configurações: Trocar foto, Alterar senha (validação), Ver/Encerrar sessões funcionam só na tela (sem login real; Sair continua avisando). As telas verbatim (Semanal da Publicidade, Diária do Detalhe) não mudam. Tag de retorno: `demo-ok` em `9949fdf`.

## 9. Riscos

- Escopo muito grande para 4 dias: mitigado pela ordem de corte e por fatias verticais.
- Calibração do seed (1.284 / 11 min / 7 em alerta simultâneos) pode tomar tempo; usar um solver simples ou seed manual por ponto.
- Fidelidade aos renders (fontes, 3 px de raio, formas de status) exige disciplina; as primitivas da fatia 0 existem para isso.
- Throughput do simulador acima de 30×: medir cedo.
- Landing local não valida demanda real; registrar na apresentação.
- Frota/Relatórios/Config exigem acesso ao arquivo do Figma (autenticação).

## 10. Processo

- O diretório não é repositório git: proponho `git init` e uma tag `demo-ok` antes do dia 26; **só commito com o seu aval**.
- Após aprovação, `pausar` e `/clear` antes de executar (custo de contexto); retomar a partir deste plano.
- Antes de declarar o protótipo pronto, uma revisão final.
