# XIAOMI BE7000

Инструкция по подготовке роутера для работы с различными компонентами (v2raya, adguardhome, прочее).

> Все команды подразумевается запускать либо с роутера, либо из этой директории (даже для любых readme во вложенных директориях).

## Установка (база)

TODO:

## Установка (общее для сервисов)

Тут прописаны общие шаги, которые нужно сделать перед установкой сервисов.

1. На внешнем накопителе создать папку `System` - в ней будут устанавливаться все необходимые зависимости для устанавлиемых утилит.
2. В директории `/data` выполнить следующее:
    1. Создать директорию `services`, в которой будут находится все скрипты для запуска конкретных сервисов:

          ```bash
          mkdir -p /data/services
          ```

    2. Скопировать в нее скрипт `startup.sh`:

          ```bash
          scp -O startup.sh root@${ROUTER_ADDRESS:-192.168.31.1}:/data
          ```

    3. Включить / выключить в этом скрипте необходимые компоненты (с помощью комментариев в функции `do_startup`)
    4. Проставить в скрипте актуальный путь до вашего внешнего устройства (переменная `USB_DIR`)
    5. Также создать директорию `scripts` для дополнительных скриптов:

        ```bash
        mkdir -p /data/scripts
        ```

3. В `/etc/config/firewall` добавить в самом конце следующее (это позволит запускать скрипт `/data/startup.sh` при каждом включение роутера):

    ```bash
    config include 'startup'
        option type 'script'
        option path '/data/startup.sh'
        option enabled '1'
    ```

4. Далее идем в интересуемые вас директории ([adguard](adguard/readme.md) или [v2raya](v2raya/readme.md)) и настраиваете согласно описанным там readme

## TODO

- [ ] Логи работают только при ручном запуске

- /etc/init.d/mi_docker disable

-
Option C — /etc/profile.d/custom_path.sh

Best practice for many systems:

sudo nano /etc/profile.d/custom_path.sh
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin