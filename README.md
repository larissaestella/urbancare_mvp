# UrbanFlow

Abrigos de ônibus inteligentes que medem a lotação de forma anônima, disparam ônibus extras antes da
superlotação e apontam pontos inseguros. Este repositório contém o protótipo completo (API, simulador e
painel web) e o componente de **Visão Computacional — Extração Automática de Endereços** do MVP CitizenTech.

| Pasta | Conteúdo |
|---|---|
| `apps/api` | FastAPI + TimescaleDB: lotação, despacho, cadastro cidadão e extração de endereços por OCR |
| `apps/sim` | Simulador dos sensores dos pontos |
| `apps/web` | React/Vite: painel do CCO, landing e tela `/cadastro-endereco` |
| `docs/` | Plano, entrevistas e o relatório `extração-automática-de-endereços.pdf` |

## Como rodar

Pré-requisito: Docker com Compose.

```bash
docker compose up -d --build
```

- Painel: <http://localhost:5173>
- Cadastro por comprovante: <http://localhost:5173/cadastro-endereco>
- API: <http://localhost:8000/docs>

Para zerar o banco: `docker compose down -v`.

## Publicação no Render

O `render.yaml` cria um Postgres e **um único serviço web**, gerado pelo `Dockerfile` da raiz. Esse serviço
roda o front compilado, a API em `/api` e o simulador, tudo no mesmo endereço.

1. Faça push do repositório para o GitHub.
2. No Render, abra **New → Blueprint**, selecione o repositório e clique em **Apply**.
3. Aguarde o build (cerca de 5–10 min). A URL pública fica no formato `https://urbanflow-xxxx.onrender.com`;
   o cadastro está em `/cadastro-endereco`.

No plano gratuito, o serviço “dorme” após 15 min sem acesso, e a primeira visita leva cerca de 1 min. O
Postgres gratuito expira em 30 dias. O schema usa TimescaleDB quando disponível e funciona sem ele.

Para testar a imagem localmente:
`docker build -t urbanflow-render . && docker run -p 8090:8000 -e DATABASE_URL=… urbanflow-render`.

## Extração Automática de Endereços

O cidadão fotografa uma conta **Enel, Vivo ou Claro** e o sistema preenche o endereço de instalação, que é
revisado, confirmado e usado pelo MVP.

### Pipeline (`apps/api/app/address_extraction.py`)

1. **Validação da entrada:** apenas JPEG, PNG e WEBP, até 10 MB e 24 MP; decodificação apenas em memória.
2. **Localização e perspectiva:** detecção do maior contorno quadrilateral da página, transformação de
   perspectiva e correção da inclinação (deskew).
3. **Pré-processamento:** recorte de 2% das bordas, remoção de ruído, CLAHE e limiarização adaptativa.
4. **Identificação do layout:** palavras-chave de cada empresa no OCR da página ou do cabeçalho.
5. **Localização do bloco do cliente**, usando as caixas e posições das palavras do OCR, não apenas regex:
   - **Enel:** linha próxima ao CPF;
   - **Claro:** “Nome do cliente” e, como alternativa, “Endereço do ponto de acesso/instalação”;
   - **Vivo:** quadro “Cadastro do Assinante”.

   Assim, endereços da empresa, de agências ou de cobrança não são confundidos com o do cliente.
6. **Ampliação e releitura:** o bloco é ampliado para 1600 e 2400 px e relido; vence a leitura com mais
   campos preenchidos e maior confiança. Leituras divergentes limitam a confiança a 0,84.
7. **Releituras especializadas** (`apps/api/app/refinement.py`), com o modelo `tessdata_best`:
   - **Vivo:** releitura precisa da linha do assinante, aceita só se CEP, cidade e UF concordarem com a
     primeira leitura;
   - **CEP (Claro e Enel):** releitura numérica quando a confiança for menor que 0,85, exigindo concordância.
8. **Saída estruturada:** `street`, `number`, `complement`, `neighborhood`, `city`, `state`,
   `postal_code`, mais o emissor e a confiança.

### Uso no MVP

1. `POST /address/extract`: recebe a foto e devolve o endereço extraído.
2. Tela `/cadastro-endereco`, acessível pelo item **“Cadastro cidadão”** no menu lateral do painel: mostra os
   campos editáveis e a confiança do OCR, e pede revisão.
3. `POST /citizens/{id}/addresses`: com **consentimento explícito**, grava o endereço confirmado, validando UF
   e CEP, e devolve os **pontos UrbanFlow da mesma via**, ordenados pela distância de numeração, com lotação,
   espera estimada e aviso de ônibus extra a caminho. Cada pessoa pode ter até 10 endereços (casa, trabalho…);
   reenviar o mesmo endereço só atualiza a data. Sem ponto na via, o endereço ajuda a priorizar novas
   instalações.
4. `GET /citizens/{id}/addresses`: lista **“Meus endereços cadastrados”**, cada um com seus pontos próximos.
5. `DELETE /citizens/{id}/addresses/{address_id}` e `DELETE /citizens/{id}/addresses`: exclusão de um ou de
   todos os endereços pelo titular. `{id}` é um identificador aleatório guardado no navegador.

### Testes e métricas

```bash
cd apps/api
pip install -r requirements.txt               # requer tesseract-ocr e tesseract-ocr-por instalados no sistema
python scripts/install_ocr_model.py           # modelo por.traineddata (tessdata_best) com checksum
export TESSDATA_BEST_DIR=~/.cache/urbanflow/tessdata-best
python -m pytest -q                           # testes unitários e documentos sintéticos com gabarito
python scripts/generate_address_fixtures.py   # (re)gera os documentos sintéticos
python scripts/build_address_report.py        # recalcula as métricas e gera o PDF em docs/
```

Os documentos de teste ficam em `apps/api/tests/fixtures/address_docs/`: duas fotos sintéticas por empresa,
em perspectivas diferentes, com gabarito em `ground_truth.json`. **Não contêm dados pessoais reais.**

Também dá para rodar os testes dentro do container: `docker compose exec api python -m pytest -q`.

### Proteção de dados (LGPD)

- A foto é processada só em memória e descartada ao fim da requisição. Nada é gravado em disco, e os
  arquivos temporários do Tesseract usam `/dev/shm`.
- Não há reconhecimento facial nem coleta de nome, CPF ou número do documento. Só o endereço confirmado é
  guardado, com consentimento, vinculado a um identificador aleatório do navegador e excluível a qualquer
  momento pela própria tela.
- Em uma publicação real, ainda são necessários HTTPS, limitação de taxa e controle de abuso, política de
  retenção e aviso de privacidade. Estas medidas técnicas não substituem uma avaliação jurídica.

### Limitações

- Funciona apenas com os três layouts suportados (Enel, Vivo, Claro). Mudanças de layout ou de rótulo exigem
  novas âncoras.
- Fotos desfocadas, com reflexo, cortadas ou muito inclinadas reduzem a acurácia, principalmente em número e
  CEP. A correção de perspectiva depende de as bordas da página estarem visíveis.
- O OCR pode errar acentos e abreviações. Por isso a confirmação humana é obrigatória antes de gravar.
- O vínculo com pontos usa o nome da via, sem geocodificação. Vias homônimas em cidades diferentes não são
  distinguidas.
- O titular é identificado só pelo navegador (sem login): quem limpar os dados do navegador perde o acesso à
  lista, e quem tiver o identificador consegue ver e excluir os endereços. Em produção, use autenticação.
- A extração é síncrona: cada foto leva alguns segundos de CPU, e há tempo limite de 20 s por chamada de OCR.
