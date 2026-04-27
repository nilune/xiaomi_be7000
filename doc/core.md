# Core

- [Автоматизация](#автоматизация)
- [Установка](#установка)

Небольшие модификации базовых вещей для роутера.

Сам UI роутера после полной настройки должен быть доступен по следующим адресам:
- <http://${ROUTER_ADDRESS}>
- <http://router>
- <http://router.lan>

## Автоматизация

```bash
uv run router deploy run core
uv run router sync pull core
uv run router sync push core
```

Автоматизация позволяет вынести общие стартовые файлы сервиса и включить его, но не заменяет ручные правки системных `/etc/config/*`, если они вам понадобятся.

## Установка

1. На внешнем накопителе в папке `System` создать подпапку `core`:

    ```bash
    cd ${ROUTER_USB_DIR}/System
    mkdir -p core
    ```

2. Копируем туда на систему сам скрипт и необходимые конфиги:

    ```bash
    scp -O -r init/_System/core/usr root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/core
    scp -O -r init/_System/core/etc root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/core
    ```

   Либо используем `uv run router deploy run core`.

3. Скопировать сам скрипт запуска core (и убедитесь что в общем скрипте `/data/startup.sh` включен запуск этого скрипта):

    ```bash
    scp -O init/data/services/core.sh root@${ROUTER_ADDRESS}:/data/services/core.sh
    scp -O init/data/startup.sh root@${ROUTER_ADDRESS}:/data/startup.sh
    ```
