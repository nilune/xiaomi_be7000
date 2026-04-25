# Architecture Plan: Router Deployment Service

Этот документ описывает архитектуру Python-сервиса для автоматизации деплоя и управления конфигурациями Xiaomi BE7000 роутера.

## Цели

1. **Автоматизация деплоя** — деплой сервисов по существующим инструкциям одной командой
2. **Двусторонняя синхронизация** — копирование конфигов роутер ↔ локальный репозиторий
3. **Централизованное конфигурирование** — один источник правды для статических IP, DNS записей и т.д.
4. **Расширяемость** — легко добавлять новые сервисы и модули
5. **Обратная совместимость** — документация остаётся актуальной, ручные команды работают

---

## Структура репозитория

```text
xiaomi_be7000/
├── CLAUDE.md
├── readme.md
├── startup.sh                    # Остаётся без изменений
│
├── adguard/                      # Существующие директории сервисов
│   ├── readme.md
│   ├── startup.sh
│   └── etc/
├── v2raya/
│   ├── readme.md
│   ├── startup.sh
│   └── etc/
├── core/
│   ├── readme.md
│   ├── startup.sh
│   └── etc/
├── filebrowser/
│   └── readme.md
│
├── deployer/                     # 🆕 Python deployment service
│   ├── pyproject.toml           # Poetry/pip dependencies
│   ├── deployer/
│   │   ├── __init__.py
│   │   ├── cli.py               # CLI entry point (click/typer)
│   │   ├── config.py            # Загрузка конфигурации
│   │   ├── connection.py        # SSH соединение с роутером
│   │   ├── sync.py              # Логика синхронизации
│   │   │
│   │   ├── services/            # Деплоеры сервисов
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # Базовый класс ServiceDeployer
│   │   │   ├── adguard.py       # AdGuard Home deployer
│   │   │   ├── v2raya.py        # V2rayA deployer
│   │   │   ├── core.py          # Core system deployer
│   │   │   └── filebrowser.py   # FileBrowser (Docker) deployer
│   │   │
│   │   ├── uci/                 # Работа с UCI конфигами
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # Базовый класс для UCI handlers
│   │   │   ├── dhcp.py          # /etc/config/dhcp
│   │   │   ├── firewall.py      # /etc/config/firewall
│   │   │   ├── wireless.py      # /etc/config/wireless
│   │   │   ├── network.py       # /etc/config/network
│   │   │   └── samba.py         # /etc/config/samba
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── ssh.py           # SSH helpers (paramiko/fabric)
│   │       ├── templating.py    # Jinja2 templates
│   │       └── placeholders.py  # Работа с __PERSONAL_N__ плейсхолдерами
│   │
│   └── templates/               # Jinja2 шаблоны конфигов
│       ├── dhcp_entries.j2      # Шаблон статических хостов для dhcp
│       ├── adguard_clients.j2   # Шаблон клиентов для AdGuard
│       └── ...
│
├── inventory/                    # 🆕 Пользовательские конфигурации
│   ├── config.yml               # Основные настройки (router_ip, usb_dir, etc.)
│   ├── hosts.yml                # Статические IP адреса (источник правды)
│   ├── dns_records.yml          # DNS перезаписи для AdGuard
│   ├── routing.yml              # RoutingA правила для v2raya
│   └── secrets.yml              # Чувствительные данные (gitignored)
│
├── backups/                      # 🆕 Бекапы с роутера
│   ├── router/                  # Бекапы /etc/config файлов
│   │   ├── dhcp
│   │   ├── firewall
│   │   ├── wireless
│   │   ├── network
│   │   └── samba
│   ├── adguard/                 # Бекапы AdGuard конфигов
│   │   └── adguardhome.yaml
│   ├── v2raya/                  # Бекапы V2rayA конфигов
│   │   └── v2raya/
│   └── .gitkeep
│
├── tmp/                          # Временные файлы (gitignored)
└── .gitignore
```

---

## Конфигурационные файлы (inventory/)

### inventory/config.yml

Основные настройки окружения:

```yaml
router:
  address: 192.168.31.1
  user: root
  usb_dir: /mnt/usb-ef8d1024

paths:
  system_dir: ${router.usb_dir}/System
  services_dir: /data/services
  log_dir: /data/usr/log

services:
  core:
    enabled: true
  adguard:
    enabled: true
    port: 3000
  v2raya:
    enabled: true
    port: 2017
  filebrowser:
    enabled: false
    port: 8088
```

### inventory/hosts.yml

Центральный источник правды для статических IP:

```yaml
# Статические IP адреса
# Из этого файла генерируются:
# - /etc/config/dhcp (статические записи)
# - /etc/adguardhome.yaml (клиенты для статистики)

networks:
  lan:
    subnet: 192.168.1.0/24
    gateway: 192.168.1.1
  miot:
    subnet: 192.168.32.0/24
    gateway: 192.168.32.1

hosts:
  # Формат: hostname, mac, ip, [network], [description]
  router:
    mac: "00:00:00:00:00:01"
    ip: 192.168.1.1
    network: lan
    description: "Main router"

  heated_towel_rail:
    mac: "d8:c8:0c:f4:56:bf"
    ip: 192.168.32.10
    network: miot
    description: "Heated towel rail controller"

  # ... другие устройства
```

### inventory/dns_records.yml

DNS перезаписи для AdGuard:

```yaml
# DNS перезаписи -> /etc/adguardhome.yaml (dns.rewrites)
records:
  # UI aliases
  router.lan: 192.168.1.1
  router: router.lan
  adguard.lan: 192.168.1.1
  adguard: adguard.lan
  v2raya.lan: 192.168.1.1
  v2raya: v2raya.lan
  
  # Custom services
  # myservice.lan: 192.168.1.100
```

### inventory/secrets.yml (gitignored)

```yaml
# Файл добавлен в .gitignore
# Содержит реальные значения вместо __PERSONAL_N__

personal:
  PERSONAL_1: "192.168.32.5"
  PERSONAL_2: "192.168.32.1"
  PERSONAL_3: "192.168.1.1"
  # ...

company:
  COMPANY_0: "example"
  # ...
```

---

## CLI команды

```bash
# Установка
pip install -e ./deployer
# или
cd deployer && poetry install

# Основные команды
router deploy [SERVICE]           # Деплой сервиса (или всех)
router deploy --services adguard,v2raya

router sync pull [SERVICE]        # Скачать конфиги с роутера в backups/
router sync push [SERVICE]        # Отправить конфиги из inventory/ на роутер

router config generate            # Сгенерировать конфиги из inventory/
router config apply               # Применить сгенерированные конфиги

# DHCP management
router dhcp leases                # Показать текущие DHCP leases с роутера
router dhcp static add <host>     # Добавить статический IP (интерактивно)
router dhcp static generate       # Сгенерировать /etc/config/dhcp из hosts.yml

# Backup
router backup create              # Создать полный бекап
router backup restore [FILE]      # Восстановить из бекапа

# Utils
router ssh                        # Открыть SSH сессию с роутером
router exec <command>             # Выполнить команду на роутере
router placeholders resolve       # Заменить __PERSONAL_N__ на реальные значения
```

---

## Архитектура классов

### Base Classes

```text
┌─────────────────────────────────┐
│         ServiceDeployer          │
│─────────────────────────────────│
│ + name: str                      │
│ + config: dict                   │
│ + connection: SSHConnection      │
│─────────────────────────────────│
│ + deploy() -> None               │
│ + pull() -> None                 │
│ + push() -> None                 │
│ + validate() -> bool             │
│ + get_backup_path() -> Path      │
└─────────────────────────────────┘
              ▲
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
┌───┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐
│AdGuard│ │V2rayA │ │ Core  │ │FileBrs│
└───────┘ └───────┘ └───────┘ └───────┘


┌─────────────────────────────────┐
│         UCIConfigHandler         │
│─────────────────────────────────│
│ + config_path: str               │
│ + connection: SSHConnection      │
│─────────────────────────────────│
│ + parse() -> dict                │
│ + generate() -> str              │
│ + apply() -> None                │
│ + pull() -> None                 │
│ + push() -> None                 │
└─────────────────────────────────┘
              ▲
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
┌───┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐
│  DHCP │ │Firewl │ │Wirelss│ │Network│
└───────┘ └───────┘ └───────┘ └───────┘
```

---

## Workflow

### 1. Первичная настройка

```bash
# 1. Клонировать репозиторий
git clone <repo>
cd xiaomi_be7000

# 2. Создать secrets.yml из шаблона
cp inventory/secrets.yml.example inventory/secrets.yml
# Отредактировать secrets.yml с реальными значениями

# 3. Установить deployer
cd deployer && poetry install

# 4. Проверить соединение
router ssh  # должен открыть SSH сессию
```

### 2. Деплой сервиса

```bash
# Деплой одного сервиса
router deploy adguard

# Деплой всех сервисов
router deploy

# Что происходит при deploy:
# 1. Читается inventory/config.yml и inventory/hosts.yml
# 2. Генерируются конфиги из шаблонов
# 3. Конфиги копируются на роутер в ${USB_DIR}/System/<service>/
# 4. startup.sh копируется в /data/services/
# 5. Выполняется /data/startup.sh (или сервис рестартится)
```

### 3. Работа со статическими IP

```bash
# Редактируем inventory/hosts.yml
vim inventory/hosts.yml

# Генерируем и применяем изменения
router dhcp static generate
router config apply --uci dhcp

# Синхронизируем с AdGuard
router sync push adguard --clients
```

### 4. Синхронизация конфигов

```bash
# Скачать все конфиги с роутера (для бекапа или редактирования)
router sync pull

# Скачать конкретный сервис
router sync pull adguard

# После локального редактирования backups/adguard/adguardhome.yaml
router sync push adguard

# SSH-редактирование на роутере -> локальный бекап
# На роутере: vim /etc/adguardhome.yaml
# Локально: router sync pull adguard
```

---

## Связь inventory и сервисов

```text
inventory/hosts.yml
        │
        ├──────────────────────┐
        │                      │
        ▼                      ▼
┌───────────────┐    ┌─────────────────────┐
│ DHCP Handler  │    │ AdGuard Handler      │
│               │    │                      │
│ Генерирует:   │    │ Генерирует:          │
│ /etc/config/  │    │ /etc/adguardhome.    │
│ dhcp          │    │ yaml (clients)       │
└───────────────┘    └─────────────────────┘
        │                      │
        ▼                      ▼
  /etc/config/dhcp     /etc/adguardhome.yaml
  (статические IP)     (клиенты для статистики)
```

---

## Обработка плейсхолдеров

Система поддерживает два режима работы:

### 1. Development (с плейсхолдерами)

Файлы в репозитории содержат `__PERSONAL_N__`, `__COMPANY_N__`:

- Безопасный коммит в Git
- Документация работает как шаблон

### 2. Production (с реальными значениями)

При деплое плейсхолдеры заменяются из `inventory/secrets.yml`:

```python
def resolve_placeholders(content: str, secrets: dict) -> str:
    """Replace __PERSONAL_N__ and __COMPANY_N__ with actual values."""
    for key, value in secrets.get('personal', {}).items():
        content = content.replace(f"__{key}__", str(value))
    for key, value in secrets.get('company', {}).items():
        content = content.replace(f"__{key}__", str(value))
    return content
```

---

## Интеграция с существующей документацией

### Принципы обратной совместимости

1. **Ручные команды остаются рабочими**
   - Все `scp -O` команды из readme.md продолжают работать
   - Deployer — это надстройка, не замена

2. **Файлы сервисов не перемещаются**
   - `adguard/`, `v2raya/`, `core/` остаются на своих местах
   - Deployer использует эти же файлы

3. **Документация — источник истины**
   - Если в readme.md написано сделать X, deployer делает X
   - Изменения в инструкциях должны отражаться в коде deployer

4. **Бекапы не коммитятся**
   - `backups/` добавлен в `.gitignore`
   - Только шаблоны и inventory коммитятся

---

## Расширение новыми сервисами

Для добавления нового сервиса:

```python
# deployer/services/my_service.py
from deployer.services.base import ServiceDeployer

class MyServiceDeployer(ServiceDeployer):
    name = "my_service"
    
    def deploy(self):
        # 1. Создать директорию на USB
        # 2. Скопировать бинарники и конфиги
        # 3. Создать симлинки
        # 4. Запустить сервис
        pass
    
    def pull(self):
        # Скачать конфиги с роутера
        pass
    
    def push(self):
        # Отправить конфиги на роутер
        pass
```

```python
# deployer/services/__init__.py
SERVICES = {
    "adguard": AdGuardDeployer,
    "v2raya": V2rayADeployer,
    "core": CoreDeployer,
    "my_service": MyServiceDeployer,  # Добавить сюда
}
```

---

## Следующие шаги

1. **Создать структуру директорий**
   - `deployer/` с базовой структурой
   - `inventory/` с примерами конфигов
   - `backups/` с `.gitkeep`

2. **Реализовать базовые модули**
   - `connection.py` — SSH через sshpass
   - `config.py` — загрузка YAML конфигов
   - `cli.py` — базовые команды

3. **Реализовать UCI handlers**
   - Начать с `dhcp.py` (наиболее востребованный)

4. **Реализовать сервисы**
   - Начать с `adguard.py` (наиболее полный пример)

5. **Интегрировать hosts.yml**
   - Генерация dhcp записей
   - Генерация AdGuard клиентов

6. **Документировать**
   - Обновить readme.md с новой секцией про deployer
   - Добавить примеры использования
