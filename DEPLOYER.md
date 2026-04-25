# Router Deployer

Утилита для управления конфигурацией роутера Xiaomi BE7000.

## Установка

1. Установи [uv](https://docs.astral.sh/uv/getting-started/installation/) согласно официальной документации.

2. Установи зависимости:
   ```bash
   uv sync
   ```

3. Скопируй `.env.example` в `.env` и укажи пароль:
   ```bash
   cp .env.example .env
   # Отредактируй .env, укажи ROUTER_SSH_PASSWORD
   ```

4. Скопируй `inventory/hosts.yml.example` в `hosts.yml` и заполни свои устройства:
   ```bash
   cp inventory/hosts.yml.example inventory/hosts.yml
   ```

## Запуск

Все команды запускаются через `uv run`:

```bash
uv run router --help
```

## Команды

```bash
# Показать конфигурацию
uv run router config show

# Проверить соединение
uv run router config validate

# DHCP leases (текущие аренды)
uv run router dhcp leases

# Статические IP: предпросмотр изменений
uv run router dhcp static --preview

# Статические IP: применить изменения
uv run router dhcp static --apply

# Скачать все конфиги с роутера
uv run router sync pull --all

# Deploy: предпросмотр
uv run router deploy run --dry-run

# AdGuard: показать клиентов из hosts.yml
uv run router adguard clients

# Выполнить команду на роутере
uv run router utils exec "uptime"
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
│   └── hosts.yml           # Статические IP (в .gitignore)
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

При применении (`uv run router dhcp static --apply`):
- Используются UCI команды - не перезаписывает весь конфиг
- Добавляет `option name` для каждого хоста
- Требуется `service dnsmasq restart` на роутере

## Безопасность

- `.env` и `hosts.yml` добавлены в `.gitignore`
- Пароль через переменную окружения или `.env`
- DHCP изменения через UCI - безопасно
