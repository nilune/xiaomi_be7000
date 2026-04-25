# Router Deployer

Утилита для управления конфигурацией роутера Xiaomi BE7000.

## Установка

```bash
# Установить uv (если нет)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Установить зависимости
uv sync

# Активировать окружение
source .venv/bin/activate
```

## Настройка

1. Скопируй `.env.example` в `.env` и укажи пароль:
   ```bash
   cp .env.example .env
   # Отредактируй .env, укажи ROUTER_SSH_PASSWORD
   ```

2. Проверь `inventory/config.yml` - там должен быть правильный IP роутера.

## Команды

```bash
# Показать конфигурацию
router config show

# Проверить соединение
router config validate

# DHCP leases (текущие аренды)
router dhcp leases

# Статические IP: предпросмотр изменений
router dhcp static --preview

# Статические IP: применить изменения
router dhcp static --apply

# Статические IP: показать сгенерированный конфиг
router dhcp static --generate

# Скачать все конфиги с роутера
router sync pull --all

# Скачать конфиг конкретного сервиса
router sync pull adguard

# Отправить конфиг на роутер
router sync push adguard

# Deploy: предпросмотр
router deploy run --dry-run

# Deploy: выполнить
router deploy run

# AdGuard: показать клиентов из hosts.yml
router adguard clients

# AdGuard: добавить клиентов в конфиг
router adguard clients --apply

# Выполнить команду на роутере
router utils exec "uptime"
```

## Структура

```
├── src/router_deployer/    # Python пакет
│   ├── cli.py              # CLI команды
│   ├── config.py           # Загрузка конфигурации
│   ├── connection.py       # SSH соединение
│   ├── services/           # Деплоеры сервисов
│   └── uci/                # UCI обработчики
├── inventory/
│   ├── config.yml          # Настройки роутера
│   └── hosts.yml           # Статические IP
├── backups/                # Скачанные конфиги
├── adguard/                # Файлы AdGuard Home
├── v2raya/                 # Файлы V2rayA
└── core/                   # Системные файлы (nginx)
```

## hosts.yml

Центральный источник правды для статических IP:

```yaml
hosts:
  my_device:
    mac: "aa:bb:cc:dd:ee:ff"
    ip: 192.168.31.100
    description: "My Device"
```

При применении (`router dhcp static --apply`):
- Используются UCI команды - не перезаписывает весь конфиг
- Добавляет `option name` для каждого хоста
- Требуется `service dnsmasq restart` на роутере

## Безопасность

- `.env` файл добавлен в `.gitignore`
- Пароль можно передать через переменную окружения или `.env`
- DHCP изменения через UCI - безопасно
