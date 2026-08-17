# Início rápido no seu Mac

Você já possui o `watermarks-remover` funcionando em `127.0.0.1:18765`. Portanto, a forma mais rápida de testar a plataforma é usar esse serviço existente.

## Terminal 1. Servidor watermarks-remover

```bash
cd ~/Developer/watermarks-remover
python3 service/scripts/server.py --host 127.0.0.1 --port 18765
```

Deixe essa janela aberta.

Confirme em outra janela:

```bash
curl -sS http://127.0.0.1:18765/health
```

## Terminal 2. Plataforma web

Descompacte este projeto, entre na pasta e execute:

```bash
cd document_forensics_web
./scripts/run-local-mac.sh
```

O script cria o ambiente virtual Python, instala as dependências e inicia a aplicação em:

```text
http://127.0.0.1:8080
```

Abra esse endereço no Chrome.

## Uso

1. Arraste o DOCX/PDF/imagem para a área de upload.
2. Clique em **Analisar arquivo**.
3. Consulte o relatório técnico.
4. Se desejar, clique em **Gerar cópia higienizada**.
5. Baixe o arquivo `_cleaned`.

O arquivo original não é sobrescrito.

## Se preferir Docker

Com Docker Desktop instalado:

```bash
cp .env.example .env
docker compose up --build -d
```

Nesse modo, o Compose sobe também um `watermarks-remover` isolado para a aplicação, sem depender do serviço da porta 18765.
