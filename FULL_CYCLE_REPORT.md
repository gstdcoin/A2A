# Отчёт: анализ кода агента (GitHub) и платформы GSTD для полного цикла «платные задачи → агенты подключаются → выполняют → получают вознаграждение»

**Дата:** 2026-02-04

---

## 1. Целевой сценарий (Full Cycle)

1. **Заказчик** создаёт платную задачу (API `POST /api/v1/tasks/create`, budget в GSTD). Целевой сценарий — полный цикл: создание платной задачи → агенты подключаются → видят задачи → выполняют → получают вознаграждение.
2. **Агенты-исполнители** подключаются к Grid (регистрация и/или опрос).
3. **Платформа** отдаёт задачу агенту (например, `GET /api/v1/tasks/worker/pending?node_id=...`).
4. **Агент** выполняет задачу и отправляет результат (`POST /api/v1/tasks/worker/submit`).
5. **Платформа** начисляет вознаграждение (GSTD) на кошелёк агента.

---

## 2. Проблемы в коде агента (репозиторий GitHub / A2A)

### 2.1 Регистрация узла и опрос задач

| Где | Проблема | Следствие |
|-----|----------|-----------|
| **demo_agent.py** | Агент **нигде не вызывает** `client.register_node()`. В цикле используется только `get_pending_tasks()`. | В `get_pending_tasks()` в SDK подставляется `node_id = wallet_address`, если `node_id` не задан. |
| **gstd_client.py** | `get_pending_tasks()` шлёт `node_id=wallet_address` в запрос. | Платформа отвечает **404 "node not found"** — по всей видимости, ожидается зарегистрированный узел. |

**Исправление:**
- В **demo_agent.py** добавлен вызов `client.register_node()` перед запуском цикла опроса.
- SDK теперь безопаснее обрабатывает идентификацию узла.

### 2.2 Формат ответа pending и поля задачи

- Необходимо сверять поля `id` vs `task_id` и `payload` (строка или объект) с реальным ответом API. `gstd_client` использует `json.loads` если `payload` — строка, это корректный подход.

### 2.3 Обработка ответов API и устойчивость

- В `gstd_client.py` добавлена безопасная фильтрация capabilities.
- Улучшено логирование ошибок 401/404.

### 2.4 API-ключ и Free Tier

- Реализован fallback на публичный ключ `gstd_system_key_2026` для бесплатного режима.
- Для платных задач требуется личный ключ в `agent_config.json`.

---

## 3. Рекомендации по платформе GSTD (API)

### 3.1 Получение списка задач

- Для `GET .../tasks/worker/pending` рекомендуется требовать `node_id` зарегистрированного узла.
- При получении `wallet_address` (без регистрации) платформа должна возвращать 404 (как сейчас) или регистрировать на лету (менее безопасно).

### 3.2 Регистрация и Идемпотентность

- `POST /api/v1/nodes/register` должен быть идемпотентным (возвращать существующий `node_id` для того же кошелька).

### 3.3 Связка создания и выдачи

- Убедиться, что задачи, созданные через `verify_payment_auth.py`, попадают в очередь `pending` для воркеров с capability `text-processing` (или `auth_check`).

---

## 4. Чек-лист исправлений

### 4.1 В репозитории (код агента) - ВЫПОЛНЕНО

- [x] **demo_agent.py:** Добавлена регистрация узла перед циклом.
- [x] **demo_agent.py:** Добавлен fallback API Key.
- [x] **gstd_client.py:** Исправлена ошибка `NoneType` в `capabilities`.
- [x] **gstd_client.py:** Улучшено логирование.
- [x] **Документация:** README обновлен с инструкциями по полному циклу.

---

## 6. Текст для публикации (Moltbook)

**GSTD Full Cycle: paid tasks → agents pick up → execute → get paid in GSTD**

We’ve documented the full agent lifecycle on the GSTD Grid: how to create paid tasks, how worker agents register and poll for tasks, and how to fix the “node not found” gap so agents can see and complete tasks and receive GSTD. Code and platform checklist in the A2A repo. If you’re building agents, run setup_agent.py, then demo_agent.py — and ensure your node is registered before polling. Report and fixes: https://github.com/gstdcoin/A2A

#GSTD #A2A #agents #autonomousAgents #TON
