# V2rayA

Сервис для проксирования запрос через прокси или что-то еще, что у вас есть.

## Установка

Сделана на основе наработок коллег:
- [тг](https://t.me/xiaomi_be7000/1464/16668) от @T7m ([ссылка на github](https://github.com/Tesla777m/xiaomi_native_v2rinst))
- [тг](https://t.me/xiaomi_be7000/1464/16868) от @Frogost

1. Скачать пакеты с сайта <https://archive.openwrt.org/releases/24.10.0-rc1/packages/aarch64_generic/packages/>:
    - `v2ray-core_5.30.0-r1_aarch64_generic.ipk`
    - `v2raya_2.2.7.3-r1_aarch64_generic.ipk`
2. `ipk` переименовать в `tar.gz`. Распаковать архивы. Достать из распакованных данных новые архивы - `data.tag.gz`, их тоже распаковать и получим необходимые две папки `data`.
3. Также скачиваем последнее ядро `xray` (<https://github.com/xtls/xray-core/releases>) с расширением `linux-arm64-v8a` (ищем максимально последнюю версию). Распаковываем и переименованием `xray` в `v2ray`.
4. На внешнем накопителе в папке `System` создать подпапку `v2raya` (тут будут храниться все необходимое для сервисов). В эту папку копируем всё из папки `data`:

    ```bash
    scp -O -r v2ray-core_5.30.0-r1_aarch64_generic/data/* root@${ROUTER_ADDRESS:-192.168.31.1}:${USB_DIR:-/mnt/usb-1210d517}/System/v2raya
    scp -O -r v2raya_2.2.7.3-r1_aarch64_generic/data/* root@${ROUTER_ADDRESS:-192.168.31.1}:${USB_DIR:-/mnt/usb-1210d517}/System/v2raya
    scp -O -r Xray-linux-arm64-v8a/v2ray root@${ROUTER_ADDRESS:-192.168.31.1}:${USB_DIR:-/mnt/usb-1210d517}/System/v2raya/usr/bin/v2ray
    ```

5. Копируем обновленные скрипты и конфиги туда же поверх старых:

    ```bash
    scp -O -r v2raya/etc/* root@${ROUTER_ADDRESS:-192.168.31.1}:${USB_DIR:-/mnt/usb-1210d517}/System/v2raya/etc
    ```

6. Скопировать сам скрипт запуска v2raya (и убедитесь что в общем скрипте `/data/startup.sh` включен запуск этого скрипта):

    ```bash
    scp -O v2raya/startup.sh root@${ROUTER_ADDRESS:-192.168.31.1}:/data/services/v2raya.sh
    ```

7. Тестируем запуск:

    ```bash
    /data/startup.sh
    ```

## Настройка

### Списки geo

1. Копируем скрипт регулярного обновления списков get:

    ```bash
    scp -O -r v2raya/scripts/* root@${ROUTER_ADDRESS:-192.168.31.1}:/data/scripts
    ```

2. Добавляем его в регулярный авто-запуск по ночам в файл `/etc/crontabs/root` в конце:

    ```bash
    # Update V2RayA configs
    0 5 * * 1 /data/scripts/update_geo_files.sh 2>&1
    ```

### Сам сервис

TODO:

### DNS (не нужно, если настраиваете AdGuardHome)

TODO:

## Обновления и удаления

TODO:
