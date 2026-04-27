# Architecture Plan: Router Deployment Service

Текущая архитектура сведена к двум состояниям репозитория:

- `init/` — стартовые, коммитируемые файлы
- `sync/` — локальная синхронизация с реальным состоянием роутера

## Цели

1. Деплоить только безопасные стартовые файлы сервиса.
2. Не пытаться хранить отдельный `inventory` для DHCP.
3. Синхронизировать файлы по их реальным путям на роутере.
4. Разделить документацию, стартовые файлы и живое состояние.

## Новая структура

```text
.
├── config.yml.example
├── init/
│   ├── _System/
│   │   ├── adGuardHome/
│   │   ├── core/
│   │   └── v2raya/
│   ├── data/
│   │   ├── startup.sh
│   │   ├── services/
│   │   └── scripts/
│   └── etc/config/
│       ├── dhcp
│       ├── firewall
│       ├── network
│       └── wireless
├── sync/
│   ├── _System/
│   ├── data/
│   └── etc/
├── doc/
│   ├── adguard.md
│   ├── core.md
│   ├── filebrowser.md
│   ├── v2raya.md
│   └── examples/
└── src/router_deployer/
```

## Что лежит в `init/`

- файлы, которые нужны для первичного включения сервиса
- скрипты в `/data`
- содержимое `_System/<service>`
- примеры ручных изменений для системных `etc/config/*`

Важно: файлы из `init/etc/config/{dhcp,firewall,network,wireless}` не являются источником правды и не должны автоматически применяться.

## Что лежит в `sync/`

`sync/` зеркалирует реальные пути роутера:

- `/etc/config/dhcp` -> `sync/etc/config/dhcp`
- `/data/startup.sh` -> `sync/data/startup.sh`
- `${ROUTER_USB_DIR}/System/v2raya/etc` -> `sync/_System/v2raya/etc`

Папка не коммитится и живет как рабочее зеркало состояния роутера.

## Deploy Flow

1. CLI читает `config.yml`.
2. Для включенных сервисов выбираются файлы из `init/`.
3. В `_System` копируются только стартовые файлы сервиса.
4. В `/data/services` и `/data/scripts` копируются нужные shell-скрипты.
5. Системные `etc/config/dhcp|firewall|network|wireless` не трогаются.

## Sync Flow

`sync pull` и `sync push` работают по явному манифесту управляемых путей:

- системные UCI-конфиги
- `/data/startup.sh`
- сервисные скрипты в `/data/services` и `/data/scripts`
- сервисные конфиги в `_System`
- отдельные runtime-конфиги вроде `/etc/adguardhome.yaml`, `/etc/v2raya`, `/etc/xray`

Это убирает старую проблему со вложенными путями вида `backups/v2raya/v2raya/v2raya`.

## DHCP Flow

Отдельный inventory для DHCP больше не используется.

CLI работает напрямую с `/etc/config/dhcp`:

- `router dhcp leases`
- `router dhcp hosts`
- `router dhcp add <name> <mac> <ip>`
- `router dhcp remove <value> --by name|ip|mac|section`

Таким образом источником правды является сам роутер плюс локальный `sync/etc/config/dhcp`.
