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

Платные запросы остаются отдельными: [баланс платформы](https://app.gstdtoken.com/payments) или [mainnet escrow · бета](https://app.gstdtoken.com/escrow-mainnet). Ограниченное делегирование обеспеченного баланса описано ниже. Автономные blockchain-подписи не предоставляются. Первый реальный mainnet-цикл всё ещё требует средств и подписей владельцев.

`/mcp` на платформе не является развёрнутым MCP-сервисом. Этот коннектор использует локальный stdio; web/mobile-хосту без локальных процессов нужен HTTP/OpenAPI-клиент либо отдельно размещённый проверенный MCP-сервер. Старые Python MCP/wallet-инструменты в репозитории — отдельный экспериментальный код; новый коннектор их не импортирует.

## English

Install Node.js 18+, clone the master branch, run `npm ci` and `npm run build` in `gstd-agent-connector`, then configure your MCP host to execute `node /absolute/path/dist/server.mjs`. Default tools are `gstd_status` and `gstd_models`; no wallet or node is created.

To enable `gstd_free_inference`, the owner sets `GSTD_AGENT_ALLOW_INFERENCE=1`, an allowed-model list (default `auto`) and `GSTD_AGENT_MAX_REQUESTS` (default 10, maximum 50). Each request also needs explicit transmission consent and a zero GSTD ceiling. The host obtains user permission. Counters are per process, not durable financial budgets; restarting does not bypass platform quotas. Failures consume dispatched attempts. Rate limits cause backoff, never automatic retries. Exact paid models are refused; auto explicitly selects the node default. Returned text is untrusted.

HTTP services can use the public OpenAPI and POST /api/v1/agents/infer with the JSON above. Never attach credentials: the route rejects wallet, session and enterprise-key headers. Existing inference quotas still apply.

Canonical node software executes funded jobs; installing or running this consumer connector does not earn tokens. Optional bounded platform-balance allowances are described below. Transfers and blockchain signing are excluded. Paid ledger and per-job escrow workflows remain separate; a real mainnet payout is still unverified.

The portable plugin manifest and `mcp.json` describe a **local** server. The self-contained build requires Node.js and includes third-party notices. No public plugin-directory submission, account installation or hosted MCP endpoint is claimed.

## Платный доступ без повторных подписей / Bounded paid access

1. Откройте https://app.gstdtoken.com/ru/agent-access (English: /agent-access), подключите TON mainnet кошелёк и выполните вход.
2. Выберите точную модель и конкретных исполнителей, общий бюджет (до 1000 GSTD), максимум за запрос и срок (до 7 дней). Кошелёк подписывает текст разрешения; это не перевод TON.
3. Разрешение принимает непустые ответы указанной модели автоматически. Это доверие выбранному оператору, а не криптографическое доказательство качества или фактически запущенных весов модели. Не отправляйте секреты.
4. Скачайте приватный gstd-agent-grant.json. Не присылайте его агенту, не коммитьте, не публикуйте и не кладите в общую папку. Настройте путь в MCP-сервере: GSTD_AGENT_GRANT_FILE=/absolute/private/path/gstd-agent-grant.json. В конфигурации хранится только путь, не токен.
5. Доступны gstd_spending_status, gstd_paid_inference, gstd_paid_receipt. Для платного вызова нужны request_id (8–100 букв/цифр/_/-), точная модель, allow_network:true, строковый предел max_cost_gstd, например "0.005". Сохраните request_id до отправки. После таймаута проверяйте receipt; не отправляйте новый ID автоматически.
6. Локальный максимум из файла дополнительно ограничивает запрос; сервер атомарно ограничивает общий бюджет, попытки, модели, исполнителей и срок. Перезапуск Codex лимит не сбрасывает. Возврат возвращает денежный лимит, но не попытку.
7. На странице можно отозвать разрешение. Новые резервирования блокируются; уже зарезервированное задание может завершиться. Текст ответа хранится приватно 10 минут; платёжная квитанция остаётся без повторного списания.

Лимит не пополняет баланс. Требуется обеспеченный депозит GSTD в существующий баланс платформы. Промокредиты и невыверенные старые балансы не расходуются. Оплата распределяется 85/10/5. При сбое, пустом ответе или несовпадении модели резерв возвращается. Вывод, подписи TON и per-job escrow остаются отдельными операциями владельцев. Этот механизм не делает ledger автономным от платформы; это контролируемое делегирование расходов внутри неё. Реальный mainnet денежный цикл всё ещё требует токенов и отдельной проверки.

English: Create a permission at /agent-access with a verified mainnet wallet. Sign the exact policy once, download the private credential, and set only its absolute file path in GSTD_AGENT_GRANT_FILE. The file contains token and a local string max_cost_gstd cap. Do not paste it into a conversation. Paid tools enforce persistent server budgets, exact models, executor payout snapshots, request limits and expiry. Record request_id before sending; uncertain outcomes require receipt lookup, not a new request. Revocation blocks new reservations, while existing reservations may finish. This spends backed platform credits only: no seed access, TON signing, withdrawals, or on-chain allowance contract. Responses are automatically accepted by the signed policy, not cryptographically verified for quality. Mainnet settlement remains separately unverified.

## USD-ориентир и котировки / USD-referenced offers

Оператор публикует свою минимальную долю на https://app.gstdtoken.com/ru/node-economics. Цена покупателя учитывает 85/10/5 и переводится в GSTD по наблюдению курса. Это не гарантия прибыли, не привязка GSTD к доллару и не выплата USDT.

Для такого предложения сначала вызовите gstd_paid_quote с тем же prompt/model/max_tokens и вашим строковым max_cost_gstd. Котировка ничего не списывает. Если within_cost_cap=false, не повышайте предел самостоятельно. Передайте quote_id в отдельный gstd_paid_inference только при существующем разрешении и достаточном бюджете. Сохраните request_id до отправки. Одна котировка не может оплатить два разных задания; при неясном исходе проверяйте квитанцию. Просроченную котировку нужно получить заново до оплаты; автоматического повтора платного запроса нет.

English: gstd_paid_quote obtains a short-lived operator USD-referenced GSTD quote without payment. Call paid inference separately with the same prompt/model/token budget and quote_id, within owner and local caps. Quotes expire after 90 seconds and are single-use for new paid jobs. This does not expand any allowance, guarantee profit or provide stablecoin payouts. Legacy tariffs remain for nodes that have not configured an offer. See https://github.com/gstdcoin/ai/blob/main/docs/MARKET_PRICING.md.
