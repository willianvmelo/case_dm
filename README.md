# API de Transações

Serviço backend desenvolvido com **FastAPI** para processamento de transações financeiras, garantindo o envio ao banco parceiro mesmo em caso de falhas temporárias.

---

## Funcionalidades

- API REST com FastAPI
- Separação clara de camadas: Controller → Service → Repository
- Persistência com SQLite
- Idempotência baseada em `external_id`
- Integração HTTP com banco parceiro (via httpx)
- Política de retry com backoff exponencial
- Limite máximo de tentativas com status FAILED
- Loop de retry em background
- Logs estruturados
- Correlation ID por requisição (`X-Request-Id`)
- 100% cobertura de testes unitários
- Docker + Docker Compose

---

## Visão Geral da Arquitetura

```
Cliente
   │
   ▼
FastAPI (Camada de API)
   │
   ▼
TransactionService (Regra de Negócio)
   │
   ▼
SqliteTransactionRepository (Persistência)
   │
   ▼
Banco Parceiro Externo (HTTP)
```

Fluxo de retry:

1. Transação é recebida.
2. Sistema tenta enviar ao parceiro.
3. Se falhar:
   - Status vira PENDING
   - `attempts` é incrementado
   - `next_retry_at` é calculado
4. Worker em background tenta novamente quando a transação estiver elegível.
5. Se atingir o limite máximo → status vira FAILED.

---

## Executando com Docker

### Build e start

```bash
docker compose up --build
```

API disponível em:

```
http://localhost:8000
```

---

## Executando os Testes

```bash
docker compose run --rm api pytest -q
```

---

## Endpoints da API

### Health Check

```
GET /health
```

Resposta:

```json
{"status": "ok"}
```

---

### Criar Transação

```
POST /transaction
```

Body:

```json
{
  "external_id": "abc-123",
  "valor": 100,
  "kind": "credit"
}
```

Possíveis respostas:

- `200 OK` → SENT
- `202 Accepted` → PENDING

---

### Consultar Status da Transação

```
GET /transaction/{external_id}
```

Resposta:

```json
{
  "transaction_id": 1,
  "external_id": "abc-123",
  "valor": 100,
  "kind": "credit",
  "partner_transaction_id": 999,
  "status": "SENT",
  "attempts": 1,
  "last_error": null
}
```

---

## Política de Retry

- Backoff exponencial: `2^n` segundos
- Delay máximo configurável
- Limite máximo de tentativas configurável
- Status FAILED evita loops infinitos

---

## Decisões Técnicas

### Por que SQLite?

- Leve
- Persistente
- Não exige infraestrutura adicional
- Fácil evoluir para outro banco

### Por que Repository + Service?

- Separação de responsabilidades
- Facilita testes unitários
- Permite trocar camada de persistência facilmente

### Por que ContextVar para request ID?

- Permite correlação de logs por requisição
- Seguro para código assíncrono

---

## Logging

Todos os logs incluem:

- `request_id`
- `external_id` (quando disponível)
- número da tentativa (em caso de retry)

Exemplo:

```
2025-01-01 INFO request_id=abc123 transactions partner_send_failed
```

---

## Como testar com cURL

> Assumindo API em `http://localhost:8000`.

### Health
```bash
curl -X GET http://localhost:8000/health
```

### Criar transação
```bash
curl -i -X POST http://localhost:8000/transaction   -H "Content-Type: application/json"   -d '{
    "external_id": "tx-001",
    "valor": 100,
    "kind": "credit"
  }'
```

### Idempotência (chame duas vezes; deve retornar o mesmo `transaction_id`)
```bash
curl -i -X POST http://localhost:8000/transaction   -H "Content-Type: application/json"   -d '{
    "external_id": "tx-001",
    "valor": 999,
    "kind": "credit"
  }'
```

### Consultar status
```bash
curl -X GET http://localhost:8000/transaction/tx-001
```

### Correlation ID (request id customizado)
```bash
curl -i -X GET http://localhost:8000/health   -H "X-Request-Id: meu-id-custom"
```

---

### Testando o mock diretamente

Sucesso:
```bash
curl -i -X POST "http://localhost:9000/bank_partner_request"   -H "Content-Type: application/json"   -d '{"external_id":"tx-mock-1","valor":100,"kind":"credit"}'
```

Falha (503):
```bash
curl -i -X POST "http://localhost:9000/bank_partner_request?fail=true"   -H "Content-Type: application/json"   -d '{"external_id":"tx-mock-2","valor":200,"kind":"debit"}'
```

Lentidão (ex.: 3000ms):
```bash
curl -i -X POST "http://localhost:9000/bank_partner_request?delay_ms=3000"   -H "Content-Type: application/json"   -d '{"external_id":"tx-mock-3","valor":300,"kind":"credit"}'
```

### Testando via API com o mock

Criar transação (deve virar `SENT` quando o mock está OK):
```bash
curl -i -X POST "http://localhost:8000/transaction"   -H "Content-Type: application/json"   -d '{"external_id":"tx-using-mock-1","valor":100,"kind":"credit"}'
```

Se o mock estiver falhando (503), a API deve retornar `202 Accepted` com `PENDING` e o retry em background tentará novamente quando a transação ficar “due”.

---

## Possíveis Evoluções

- Separar API e Worker em containers distintos
- Implementar RabbitMQ com DLQ
- Observabilidade com métricas (Prometheus)
- Logging estruturado em JSON
- Circuit breaker para o parceiro
- Ajustes para ambiente de produção
