# Document Provenance Analyzer

Aplicação web para upload, inspeção técnica, análise de proveniência e geração de cópia higienizada de documentos. O motor principal de inspeção/limpeza é o `watermarks-remover`; o projeto acrescenta uma camada forense própria para DOCX e imagens.

## O que o MVP faz

- Upload via navegador.
- Inspeção automática pelo `watermarks-remover`.
- Análise aprofundada de DOCX:
  - `docProps/core.xml` e `docProps/app.xml`;
  - RSIDs e controle de alterações;
  - comentários, content controls e campos Word;
  - caracteres Unicode invisíveis/suspeitos;
  - `customXml` e indicadores de SharePoint/Content Type;
  - imagens em `word/media/`, EXIF e metadados de software;
  - timestamps internos do pacote ZIP.
- Cálculo de SHA-256.
- Relatório JSON completo.
- Botão para gerar uma nova cópia `_cleaned`, sem sobrescrever o original.
- Reinspeção automática da cópia higienizada.
- Exclusão automática dos jobs após o TTL configurado.

## Limite interpretativo

A ferramenta identifica sinais técnicos verificáveis. Ela não prova autoria humana, não determina fraude e não garante que detectores proprietários de IA deixarão de identificar um conteúdo.

## Opção A. Rodar tudo com Docker. Recomendado

Esta opção sobe dois containers:

1. `web`: esta plataforma FastAPI.
2. `watermarks`: o serviço `watermarks-remover`, usando a imagem publicada que inclui ferramentas auxiliares do core.

### 1. Entre na pasta

```bash
cd document_forensics_web
```

### 2. Crie o `.env`

```bash
cp .env.example .env
```

Edite a chave antes de uso real:

```env
WATERMARKS_API_KEY=uma-chave-grande-e-aleatoria
```

### 3. Suba a aplicação

```bash
docker compose up --build -d
```

### 4. Abra no navegador

```text
http://127.0.0.1:8080
```

### 5. Ver logs

```bash
docker compose logs -f
```

### 6. Encerrar

```bash
docker compose down
```

## Opção B. Usar o watermarks-remover que já está instalado no Mac

Se o seu serviço já roda em:

```text
http://127.0.0.1:18765
```

confirme:

```bash
curl -sS http://127.0.0.1:18765/health
```

Depois, nesta pasta:

```bash
./scripts/run-local-mac.sh
```

Abra:

```text
http://127.0.0.1:8080
```

### Execução manual sem script

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export WATERMARKS_SERVICE_URL="http://127.0.0.1:18765"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

## API da plataforma

### Saúde

```http
GET /api/health
```

### Analisar arquivo

```http
POST /api/analyze
Content-Type: multipart/form-data
file=<arquivo>
```

Retorna `job_id`, SHA-256, relatório do serviço, análise forense e resumo.

### Higienizar

```http
POST /api/clean/{job_id}
```

Gera uma nova cópia `_cleaned` e executa reinspeção.

### Baixar cópia higienizada

```http
GET /api/download/{job_id}/cleaned
```

### Baixar relatório JSON

```http
GET /api/download/{job_id}/report.json
```

## Estrutura

```text
app/
  main.py
  config.py
  storage.py
  security.py
  reporting.py
  watermarks_client.py
  analyzers/
    docx.py
    image.py
    generic.py
  static/
    index.html
    styles.css
    app.js
tests/
compose.yaml
Dockerfile
requirements.txt
```

## Segurança adotada no MVP

- nomes de arquivo são normalizados;
- não há caminho fornecido pelo usuário sendo usado diretamente para gravação;
- limite de upload configurável;
- DOCX é lido sem extração direta para o filesystem;
- há limites para quantidade de partes ZIP e tamanho descompactado;
- o serviço `watermarks-remover` não é exposto ao host no Compose;
- autenticação bearer entre backend e serviço interno;
- arquivos são armazenados apenas em diretório temporário por job;
- jobs expiram automaticamente;
- a limpeza sempre gera um novo arquivo.

Para produção pública, acrescente autenticação de usuários, rate limiting, antivírus/sandbox, proxy TLS, armazenamento criptografado, observabilidade e política de retenção formal.

## Testes

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

## Próximas evoluções recomendadas

- PDF de relatório técnico assinado/hashado.
- Login e organizações.
- Histórico de análises com consentimento de retenção.
- Antivírus ClamAV e fila de processamento isolada.
- Comparação estrutural DOCX original vs. cleaned mais profunda.
- Detecção de PII configurável.
- Módulo de relatórios ambientais com regras específicas para coordenadas, e-mails, CPF, processos e dados sensíveis.
