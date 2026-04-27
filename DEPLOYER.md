# Router Deployer

Утилита для управления структурой `init/`, `sync/` и точечными действиями на роутере Xiaomi BE7000.

## Статус по исходным проблемам

1. `utils exec --help` упрощен.
2. Статика DHCP больше не зависит от `hosts.yml` и AdGuard.
3. Конфигурирование AdGuard/V2rayA через `config.yml` сведено к `enabled: true/false`.
4. `backups` заменен на `sync` с отражением реальных путей роутера.
5. Сервисные стартовые файлы вынесены в `init/`.
6. `init/` и `sync/` приведены к одной логике путей: `_System`, `data`, `etc`.
7. Сервисная документация вынесена в `doc/`.
8. В сервисных readme добавлена оговорка про автоматическое включение и ручные `/etc/config`.
9. Остатки старой структуры нужно дочистить отдельно после согласования.

## Установка

```bash
uv sync
cp .env.example .env
cp config.yml.example config.yml
```

## Запуск

```bash
uv run router --help
```

## Команды

### Конфигурация

```bash
uv run router config show
uv run router config validate
```

### DHCP

```bash
uv run router dhcp leases
uv run router dhcp hosts
uv run router dhcp add camera aa:bb:cc:dd:ee:ff 192.168.31.80
uv run router dhcp remove aa:bb:cc:dd:ee:ff --by mac
```

### Синхронизация

```bash
uv run router sync pull --all
uv run router sync pull adguard
uv run router sync pull v2raya

uv run router sync push dhcp --dry-run
uv run router sync push adguard
uv run router sync push v2raya
```

### Deploy

```bash
uv run router deploy run --dry-run
uv run router deploy run
uv run router deploy run adguard
```

### Utils

```bash
uv run router utils exec "uptime"
uv run router utils exec "logread | tail -20" --show-stderr
```

## Примечания

- `sync/` не должен коммититься.
- `init/etc/config/*` содержит только примеры ручных изменений.
- для сервисов автоматизируется включение стартовых файлов, но не полная настройка системных UCI-конфигов.
