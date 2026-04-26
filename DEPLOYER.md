# Router Deployer

Утилита для управления конфигурацией роутера Xiaomi BE7000.

## Установка

```bash
uv sync                                    # Установи зависимости
cp .env.example .env                       # Укажи ROUTER_SSH_PASSWORD
cp config.yml.example config.yml           # Скопируй пример конфигурации
# Отредактируй config.yml - заполни свои устройства и настройки
```

## Запуск

```bash
uv run router --help
```

## Команды

### Конфигурация

```bash
uv run router config show      # Показать конфигурацию
uv run router config validate  # Проверить соединение
```

### DHCP + AdGuard

```bash
uv run router dhcp leases              # Текущие аренды IP
uv run router dhcp static              # Предпросмотр изменений
uv run router dhcp static --apply      # Применить DHCP изменения
uv run router dhcp static --apply --adguard --restart  # Полное обновление
```

### AdGuard

```bash
uv run router adguard clients          # Показать клиентов
uv run router adguard clients --apply  # Обновить клиентов
```

### Синхронизация

```bash
uv run router sync pull --all          # Скачать все конфиги
uv run router sync pull adguard        # Скачать конкретный конфиг
uv run router sync push dhcp --force   # Отправить конфиг
```

### Deploy

```bash
uv run router deploy run --dry-run     # Предпросмотр
uv run router deploy run adguard       # Деплой сервиса
```

## Конфигурация

### config.yml

```yaml
router:
  address: 192.168.31.1
  user: root
  usb_dir: /mnt/usb-ef8d1024

services:
  adguard:
    enabled: true
    log_level: info

  v2raya:
    enabled: true
    xray_log_level: warning

  filebrowser:
    enabled: false
    port: 8088
    sources:
      - path: /mnt/usb-ef8d1024
        name: USB Drive
      - path: /etc/config
        name: Router Config

hosts:
  air_conditioner_bedroom:
    mac: "30:c9:22:05:48:94"
    ip: 192.168.32.106
    name: "Air Conditioner Bedroom"
```

## Безопасность

- `.env` и `config.yml` в `.gitignore`
- UCI push требует `--force` для применения
