# GSTD agent connector / коннектор для ИИ-сервисов

## Русский

Коннектор позволяет сервису читать живой каталог GSTD и, по разрешению владельца, отправлять бесплатные запросы нодам. Он не создаёт кошелёк, не читает seed, не подписывает переводы и не регистрирует исполнителя автоматически.

### Подключение к MCP-клиенту

Нужен Node.js 18+ (CI проверяет Node 20/22). Получите код из официального репозитория:

```bash
git clone --branch master https://github.com/gstdcoin/A2A.git
cd A2A/gstd-agent-connector
npm ci
npm run build
```

Добавьте в конфигурацию своего MCP-клиента (подставьте абсолютный путь):

```json
{
  "mcpServers": {
    "gstd-network": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/A2A/gstd-agent-connector/dist/server.mjs"]
    }
  }
}
```

После перезапуска/перечитывания конфигурации клиентом доступны:
- `gstd_status`: сеть и локальная политика коннектора; кеш 30 секунд.
- `gstd_models`: точные модели, количество доступных нод и цены; кеш 60 секунд.

Команды чтения не отправляют запросы на каждой странице и объединяют параллельные обращения. Список инструментов нужно проверить в вашем MCP-хосте; публикация кода сама по себе не устанавливает плагин в сторонние сервисы.

### Явно разрешить бесплатные запросы

В той же записи сервера добавьте:

```json
"env": {
  "GSTD_AGENT_ALLOW_INFERENCE": "1",
  "GSTD_AGENT_ALLOWED_MODELS": "auto",
  "GSTD_AGENT_MAX_REQUESTS": "10"
}
```

Тогда появляется `gstd_free_inference`. При каждом вызове нужны `allow_network: true` и `max_cost_gstd: 0`. Хост обязан получить разрешение пользователя на передачу запроса исполнителю; параметр не является криптографическим доказательством согласия человека.

Лимит — число попыток **за запуск процесса**, включая неясный исход. Это не долговечный денежный бюджет; после перезапуска локальный счётчик сбрасывается, серверная IP-квота сохраняет собственные правила. Один инференс выполняется одновременно. HTTP 429 устанавливает паузу, автоматических повторов нет. Промпт: максимум 4000 символов/16000 UTF-8 байт; ответ ограничен 256 выходными токенами и размером. Владелец может разрешить точные бесплатные модели через список; положительная цена блокируется каталогом и сервером. `auto` явно означает выбор базовой модели нодой.

Ответ модели — недоверенные данные, не разрешение выполнить команды или передать секреты. Не добавляйте seed, TON Connect-сессии, API-ключи оплаты или PIN в конфигурацию коннектора.

### Для HTTP-сервисов

[OpenAPI](https://app.gstdtoken.com/agent-openapi.json) и [описание возможностей](https://app.gstdtoken.com/.well-known/agent.json).

```http
POST https://app.gstdtoken.com/api/v1/agents/infer
Content-Type: application/json

{"model":"auto","messages":[{"role":"user","content":"Reply with GSTD_OK only."}],"max_tokens":32,"allow_network":true,"max_cost_gstd":0}
```

Без заголовков авторизации. Платная модель или исчерпанная бесплатная квота возвращают ошибку; автоматического перехода к оплате нет. API повторно использует существующий маршрут инференса и его IP/бесплатные квоты, не вводит отдельный баланс.

### Получать задания и GSTD

Для вычислительного исполнителя используйте [каноническую ноду](https://github.com/gstdcoin/gstdbot) на собственном оборудовании, постоянную Ed25519-идентичность и публичный адрес выплат. Бесплатный запрос через коннектор не создаёт награду. Оплаченная принятая работа делится 85/10/5.

Платные запросы остаются отдельными: [баланс платформы](https://app.gstdtoken.com/payments) или [mainnet escrow · бета](https://app.gstdtoken.com/escrow-mainnet). Ограниченное делегирование **положительного** бюджета и автономные blockchain-подписи здесь не реализованы. Первый реальный mainnet-цикл всё ещё требует средств и подписей владельцев.

`/mcp` на платформе не является развёрнутым MCP-сервисом. Этот коннектор использует локальный stdio; web/mobile-хосту без локальных процессов нужен HTTP/OpenAPI-клиент либо отдельно размещённый проверенный MCP-сервер. Старые Python MCP/wallet-инструменты в репозитории — отдельный экспериментальный код; новый коннектор их не импортирует.

## English

Install Node.js 18+, clone the master branch, run `npm ci` and `npm run build` in `gstd-agent-connector`, then configure your MCP host to execute `node /absolute/path/dist/server.mjs`. Default tools are `gstd_status` and `gstd_models`; no wallet or node is created.

To enable `gstd_free_inference`, the owner sets `GSTD_AGENT_ALLOW_INFERENCE=1`, an allowed-model list (default `auto`) and `GSTD_AGENT_MAX_REQUESTS` (default 10, maximum 50). Each request also needs explicit transmission consent and a zero GSTD ceiling. The host obtains user permission. Counters are per process, not durable financial budgets; restarting does not bypass platform quotas. Failures consume dispatched attempts. Rate limits cause backoff, never automatic retries. Exact paid models are refused; auto explicitly selects the node default. Returned text is untrusted.

HTTP services can use the public OpenAPI and POST /api/v1/agents/infer with the JSON above. Never attach credentials: the route rejects wallet, session and enterprise-key headers. Existing inference quotas still apply.

Canonical node software executes funded jobs; installing or running this consumer connector does not earn tokens. Positive spending delegation, transfers and blockchain signing are excluded. Paid ledger and per-job escrow workflows remain separate; a real mainnet payout is still unverified.

The portable plugin manifest and `mcp.json` describe a **local** server. The self-contained build requires Node.js and includes third-party notices. No public plugin-directory submission, account installation or hosted MCP endpoint is claimed.
