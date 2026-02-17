# GSTD Swarm Client — Desktop-клиент для участника роя

Клиент для подключения к сети GSTD в качестве вычислительной ноды. Регистрируется, получает задачи, выполняет их и получает награды в GSTD.

**Платформы:** Windows, Linux, macOS

## Требования

- Python 3.8+
- Windows, Linux или macOS

## Быстрый старт

### 1. Получите API ключ

1. Зайдите на https://app.gstdtoken.com/dashboard
2. Подключите кошелёк
3. Создайте API ключ в разделе Sovereign / API Keys

### 2. Установка

```bash
cd A2A/swarm
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Запуск

```bash
export GSTD_API_KEY="gstd_xxxxxxxx"
export GSTD_WALLET="EQ..."   # Адрес кошелька (обязателен)

python swarm_client.py
```

Или через launcher:

**Linux / macOS:**
```bash
chmod +x run_swarm.sh
./run_swarm.sh
```

**Windows:**
```cmd
set GSTD_API_KEY=gstd_xxxxxxxx
set GSTD_WALLET=EQ...
run_swarm.bat
```

С аргументами:

```bash
python swarm_client.py --api-key gstd_xxx --wallet EQ...
```

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `GSTD_API_KEY` | API ключ (обязательно) |
| `GSTD_WALLET` | Адрес кошелька (обязательно, если не в ключе) |
| `GSTD_API_URL` | URL платформы (по умолчанию https://app.gstdtoken.com) |

## Возможности

- **Регистрация ноды** — автоматическая регистрация при старте
- **Heartbeat** — отправка каждые 25 сек для поддержания онлайн-статуса
- **Получение задач** — polling `/tasks/worker/pending`
- **WebSocket** — опционально для Fleet Commands (standby/resume)
- **Выполнение задач** — базовый обработчик (polymarket_prediction, prompt/input)

## Fleet Commands

При использовании WebSocket клиент реагирует на команды из Dashboard:

- **standby** — приостановить получение и выполнение задач
- **resume** — возобновить работу
- **clean** — (логируется, без действия)

## Запуск как сервис (systemd)

```ini
# /etc/systemd/system/gstd-swarm.service
[Unit]
Description=GSTD Swarm Client
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/A2A/swarm
Environment="GSTD_API_KEY=your_key"
Environment="GSTD_WALLET=EQ..."
ExecStart=/path/to/A2A/swarm/.venv/bin/python swarm_client.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable gstd-swarm
sudo systemctl start gstd-swarm
sudo systemctl status gstd-swarm
```

## Без WebSocket

Если `websocket-client` не установлен или нужен только REST:

```bash
python swarm_client.py --no-ws
```

## Расширение

Для кастомной обработки задач отредактируйте метод `_execute_task` в `swarm_client.py`.
