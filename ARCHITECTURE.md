# Architecture Plan: Router Deployment Service

Этот документ описывает текущую архитектуру Python-сервиса для автоматизации деплоя и синхронизации конфигураций Xiaomi BE7000.

Главная идея теперь разделена на три слоя:

- `doc/` — документация и примеры ручной настройки
- `init/` — коммитируемые стартовые файлы для первичного включения сервисов
- `sync/` — локальная рабочая копия актуального состояния роутера

## Цели

1. Автоматизировать безопасную часть деплоя.
2. Не ломать ручной workflow там, где системные UCI-правки требуют контроля.
3. Хранить service-specific состояние по реальным путям роутера.
4. Развести понятия "стартовая конфигурация" и "живое состояние".
5. Не дублировать DHCP inventory отдельно от самого роутера.

## Текущее дерево

```text
.
├── ARCHITECTURE.md
├── readme.md
├── config.yml.example
├── init/
│   ├── _System/
│   │   ├── adGuardHome/
│   │   ├── core/
│   │   ├── filebrowser/
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
│   └── etc/config/
├── doc/
│   ├── adguard.md
│   ├── core.md
│   ├── filebrowser.md
│   ├── v2raya.md
│   └── examples/
└── src/
    ├── cli.py
    ├── config.py
    ├── connection.py
    ├── sync.py
    ├── services/
    └── uci/
```

## Смысл директорий

### `doc/`

Здесь живет вся пользовательская документация:
- ручная установка сервисов
- ссылки на официальные доки и внешние статьи
- примеры `routingA`, DNS серверов и исторических бэкапов

### `init/`

Это стартовое состояние, которое можно коммитить в git и деплоить на новый роутер.

Что сюда входит:
- `init/_System/<service>` — service-specific файлы для `${ROUTER_USB_DIR}/System/<service>`
- `init/data/startup.sh` — общий startup script
- `init/data/services/*.sh` — service startup scripts
- `init/data/scripts/*` — вспомогательные router scripts
- `init/etc/config/*` — только примеры ручных системных изменений

Важно:
- `init/etc/config/*` не является источником правды
- эти системные файлы не должны автоматически пушиться на роутер

### `sync/`

Это живое локальное зеркало части файлов роутера, с которыми действительно нужно работать.

Ключевой принцип:
- в `sync/etc/config` должны лежать только четыре системных UCI-файла:
  - `dhcp`
  - `firewall`
  - `network`
  - `wireless`
- всё service-specific состояние должно лежать в `sync/_System/...`
- скрипты из `/data` должны лежать в `sync/data/...`

То есть мы специально не тянем в `sync/etc`:
- `/etc/init.d/*`
- `/etc/nginx/conf.d/*`
- `/etc/profile.d/*`
- `/etc/v2raya`
- `/etc/xray`
- `/etc/adguardhome.yaml`

Причина простая:
- это либо симлинки в `_System`
- либо runtime/generated файлы
- либо вещи, которые безопаснее редактировать только через их реальный origin в `System`

## Маппинг путей роутера

### Системные UCI-файлы

```text
/etc/config/dhcp      -> sync/etc/config/dhcp
/etc/config/firewall  -> sync/etc/config/firewall
/etc/config/network   -> sync/etc/config/network
/etc/config/wireless  -> sync/etc/config/wireless
```

### Общие data-скрипты

```text
/data/startup.sh                     -> sync/data/startup.sh
/data/services/core.sh               -> sync/data/services/core.sh
/data/services/adguardhome.sh        -> sync/data/services/adguardhome.sh
/data/services/v2raya.sh             -> sync/data/services/v2raya.sh
/data/scripts/update_geo_files.sh    -> sync/data/scripts/update_geo_files.sh
```

### `_System`

```text
${ROUTER_USB_DIR}/System/core/etc                    -> sync/_System/core/etc
${ROUTER_USB_DIR}/System/core/usr/bin/core.sh        -> sync/_System/core/usr/bin/core.sh

${ROUTER_USB_DIR}/System/adGuardHome/etc             -> sync/_System/adGuardHome/etc
${ROUTER_USB_DIR}/System/adGuardHome/adguardhome.yaml -> sync/_System/adGuardHome/adguardhome.yaml

${ROUTER_USB_DIR}/System/v2raya/etc                  -> sync/_System/v2raya/etc

${ROUTER_USB_DIR}/System/filebrowser/etc             -> sync/_System/filebrowser/etc
${ROUTER_USB_DIR}/System/filebrowser/config          -> sync/_System/filebrowser/config
${ROUTER_USB_DIR}/System/filebrowser/database        -> sync/_System/filebrowser/database
```

## Deploy Flow

`deploy` работает только с `init/`.

Общий сценарий:
1. CLI читает `config.yml`.
2. Всегда выкладывает базовый `/data/startup.sh`.
3. Выбирает включенные сервисы.
4. Для каждого сервиса копирует стартовые файлы в `_System`.
5. Для `adguard`, `v2raya` и `xray` сверяет желаемые версии и догружает бинарь только при несовпадении версии.
6. Для docker-сервисов пересоздает контейнер напрямую через `docker run --restart unless-stopped`.
7. Копирует скрипты в `/data/services` и `/data/scripts`.
8. Не трогает системные `/etc/config/dhcp|firewall|network|wireless`.

Важно:
- `deploy run startup` выкладывает только базовый `startup.sh`
- `deploy run base` является алиасом той же команды
- `enabled: false` останавливает сервис, убирает его из `startup.sh` или удаляет docker-контейнер, но не удаляет данные

Это позволяет безопасно автоматизировать включение сервиса, но не ломать вручную настроенный роутер.

## Sync Flow

`sync pull` и `sync push` работают не по "всем подряд файлам", а по явному списку управляемых путей.

Это было сделано по двум причинам:

1. Старая модель давала странные пути вида `backups/v2raya/v2raya/v2raya`.
2. Появлялось слишком много мусора в `sync/etc`, хотя реальные источники правды лежат в `_System`.

Текущий принцип:
- системные UCI-файлы живут отдельно в `sync/etc/config`
- service-specific состояние живет в `sync/_System`
- startup/service scripts живут в `sync/data`

## DHCP Flow

Отдельный `inventory/hosts.yml` больше не используется.

Источник правды для DHCP теперь сам роутер:
- `/etc/config/dhcp`
- `sync/etc/config/dhcp`

CLI работает напрямую с UCI:

```text
router dhcp leases
router dhcp hosts
router dhcp candidates
router dhcp add <name> <mac> <ip>
router dhcp remove <value> --by name|ip|mac|section
```

Таким образом:
- нет дублирования inventory
- нет рассинхронизации между роутером и локальным yaml
- статикой можно управлять точечно
- можно получить список lease-записей, которые еще не закреплены статикой
- список кандидатов можно фильтровать через `dhcp.static_candidates.exclude_macs` и `exclude_mac_prefixes` в `config.yml`

## Filebrowser

`filebrowser` теперь встроен в ту же модель, что и остальные сервисы.

Что изменено:
- появился `init/_System/filebrowser`
- конфиг и база контейнера лежат в `${ROUTER_USB_DIR}/System/filebrowser`
- первый логин/пароль задается явно из `config.yml`
- после первого старта пароль хранится в персистентной DB и дальше меняется уже через UI
- `config.yml` генерирует только `container.env`, а сам контейнер поднимается deployer-ом напрямую через Docker

То есть контейнер больше не является единственным местом хранения состояния.

## Кодовая структура

Python-код теперь лежит прямо в `src/`, без вложенного `src/router_deployer`.

Основные модули:
- `src/cli.py` — команды CLI
- `src/config.py` — загрузка `config.yml`
- `src/connection.py` — SSH/SCP доступ
- `src/sync.py` — правила sync pull/push
- `src/services/` — deployers сервисов
- `src/uci/` — работа с системными UCI-конфигами

Это упрощает packaging и делает код менее многословным.

## Ограничения

Что по-прежнему intentionally не автоматизируется полностью:
- все ручные правки системных UCI-конфигов сверх базового DHCP tooling
- сложная бизнес-логика настройки AdGuard/V2rayA через их UI
- обновление внешних бинарей из релизов GitHub
- все возможные runtime/generated файлы, которые не являются удобной точкой редактирования

Именно это разделение и является основой текущей архитектуры.
