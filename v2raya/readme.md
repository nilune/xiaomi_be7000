# V2rayA

Сервис для проксирования запрос через прокси или что-то еще, что у вас есть.

- [Установка](#установка)
- [Настройка](#настройка)
  - [Списки geo](#списки-geo)
  - [Сам сервис](#сам-сервис)
- [Обновление](#обновление)
- [Удаление](#удаление)
- [Дополнительно](#дополнительно)
  - [Работа с сервисом](#работа-с-сервисом)
  - [Бекап](#бекап)
- [Задачи](#задачи)

## Установка

Сделана на основе наработок коллег:
- [тг](https://t.me/xiaomi_be7000/1464/16668) от @T7m ([ссылка на github](https://github.com/Tesla777m/xiaomi_native_v2rinst))
- [тг](https://t.me/xiaomi_be7000/1464/16868) от @Frogost

1. Скачать пакет `xray` с <https://github.com/xtls/xray-core/releases> и `v2raya` с <https://github.com/v2rayA/v2rayA/releases>:

    ```bash
    # TODO: не работает для v2raya
    export V2RAYA_VERSION=2.2.7.3
    wget -O tmp/v2raya "https://github.com/v2rayA/v2rayA/releases/download/v${V2RAYA_VERSION}/v2raya_linux_arm64_${V2RAYA_VERSION}"
    chmod +x tmp/v2raya

    export XRAY_VERSION=26.3.27
    wget -qO ./tmp/temp.zip "https://github.com/XTLS/Xray-core/releases/download/v${XRAY_VERSION}/Xray-linux-arm64-v8a.zip" && unzip -q ./tmp/temp.zip -d ./tmp/xray && rm ./tmp/temp.zip
    ```

2. На внешнем накопителе в папке `System` создать подпапку `v2raya` (тут будут храниться все необходимое для v2raya) и пару системных папок:

    ```bash
    cd ${ROUTER_USB_DIR}/System
    mkdir -p v2raya/usr/bin
    ```

3. Копируем туда на систему сам бинарь и необходимые конфиги (да, мы формально переименовываем `xray` в `v2ray` - зачем это нужно сам не знаю):

    ```bash
    scp -O tmp/v2raya root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/v2raya/usr/bin/v2raya
    scp -O tmp/xray/xray root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/v2raya/usr/bin/v2ray
    scp -O -r v2raya/etc root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/v2raya
    ```

4. Скопировать сам скрипт запуска v2raya (и убедитесь что в общем скрипте `/data/startup.sh` включен запуск этого скрипта):

    ```bash
    scp -O v2raya/startup.sh root@${ROUTER_ADDRESS}:/data/services/v2raya.sh
    ```

5. Тестируем запуск:

    ```bash
    /data/startup.sh
    ```

## Настройка

### Списки geo

1. Копируем скрипт регулярного обновления списков get:

    ```bash
    scp -O -r v2raya/scripts/* root@${ROUTER_ADDRESS}:/data/scripts
    ```

2. Добавляем его в регулярный авто-запуск по ночам в файл `/etc/crontabs/root` в конце:

    ```bash
    # Update V2RayA configs
    0 5 * * 1 /data/scripts/update_geo_files.sh 2>&1
    ```

### Сам сервис

Все в дальнейшем настраивается через Web UI на порте **2017** (например, <http://192.168.31.1:2017>):

1. Добавляете свою подписку на VPN
2. Проставляем следующие настройки в **Settings** последовательно:
   1. Включено: режим разделения трафика такой же, как у порта с правилами
      1. IP форвардинг
      2. Port Sharing
   2. tproxy
   3. RoutingA -> см. [файл](./routingA.txt)
   4. Выключено
   5. Выключено
   6. По-умолчанию
   7. HTTP + TLS + Quic
   8. Выключено
   9. Обновлять подписки регулярно (в часах): 12
   10. Следовать за Прозрачным прокси/Системным прокси

## Обновление

Для обновления - просто обновите нужные вам компоненты в директории `${ROUTER_USB_DIR}/System/v2raya`. В том числе именно таким образом следует обновлять бинари v2ray / v2raya.

А для получение актуальных `etc` конфигов - взять пакеты `v2ray-core_5.30.0-r1_aarch64_generic.ipk` и `v2raya_2.2.7.3-r1_aarch64_generic.ipk` с сайта <https://archive.openwrt.org/releases/24.10.0-rc1/packages/aarch64_generic/packages/>. `ipk` переименовать в `tar.gz`. Распаковать этот архив. Достать из распакованных данных новый архив - `data.tag.gz`, его тоже распаковать и получим необходимую папку `data`. В ней подправить нужные конфиги и можно обновляться.

## Удаление

В целом все компоненты сервисы состоят из:
1. Директории `${ROUTER_USB_DIR}/System/v2raya` - ее можно просто удалить с помощью `rm -rf <dir>`
2. Множества симлинков в разных местах, но они будут стерты/бесполезны при перезапуске роутера
3. Запуска самого компоненты в `/data/startup.sh`
4. Скрипта запуска в `/data/services/v2raya.sh`

Поэтому удалив это - вы удалите сервис.

## Дополнительно

### Работа с сервисом

Через команды `service v2ray help` и `service v2raya help` (и подобные команды). Логи находятся по пути `/data/usr/log/v2raya/`

### Бекап

Можно забекапить путем сохранения файлов - `${ROUTER_USB_DIR}/System/v2raya/etc/v2raya`. Скопировать себе на систему можно следующим образом:

```bash
mkdir v2raya/backup
scp -O "root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/v2raya/etc/v2raya/*" v2raya/backup
```

## Задачи

- [ ] Установка v2raya через `"https://github.com/v2rayA/v2rayA/releases/download/v${V2RAYA_VERSION}/v2raya_linux_arm64_${V2RAYA_VERSION}"` не работает
- [ ] Донастроить логирование для v2ray
- [ ] Донастроить конфиг v2ray, в том числе ограничения по udp
- [ ] Возможно сделать ограничения на udp `/etc/sysctl.d/99-xray-udp.conf`: `net.netfilter.nf_conntrack_udp_timeout=15`, `net.netfilter.nf_conntrack_udp_timeout_stream=60`
- [ ] удалить настройки для v2ray - поменять на xray и явное везде указание. Удалить лишние конфиги
- [ ] xray статистика
