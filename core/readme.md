# AdGuardHome

- [Установка](#установка)

Небольшие модификации базовых вещей для роутера

## Установка

1. На внешнем накопителе в папке `System` создать подпапку `core`:

    ```bash
    cd ${ROUTER_USB_DIR}/System
    mkdir -p core
    ```

2. Копируем туда на систему сам скрипт и необходимые конфиги:

    ```bash
    scp -O -r core/usr root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/core
    scp -O -r core/etc root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/core
    ```

3. Скопировать сам скрипт запуска core (и убедитесь что в общем скрипте `/data/startup.sh` включен запуск этого скрипта):

    ```bash
    scp -O core/startup.sh root@${ROUTER_ADDRESS}:/data/services/core.sh
    ```
