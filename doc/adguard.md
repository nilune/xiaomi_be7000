# AdGuardHome

- [Автоматизация](#автоматизация)
- [Установка](#установка)
- [Настройка](#настройка)
- [Обновление](#обновление)
- [Удаление](#удаление)
- [Дополнительно](#дополнительно)
  - [Работа с сервисом](#работа-с-сервисом)
  - [Бекап](#бекап)
    - [Настройки сервиса](#настройки-сервиса)
    - [Настройки dhcp](#настройки-dhcp)

Сервис в первую очередь позволяет явно позволяет мониторить все запросы в вашей сети (кто и к чему обращается). Это в том числе важно, если какие-то запросы надо проксировать через V2ray от всяких умных устройств, но вы не знаете, к кому они идут.

Ну а также этот сервис позволяет блокировать рекламу на уровне DNS, конечно же.

Сам сервис после полной настройки должен быть доступен по следующим адресам:
- <http://${ROUTER_ADDRESS}:3000>
- <http://adguard>
- <http://adguard.lan>

Ссылки:

- [Github](https://github.com/AdguardTeam/AdGuardHome)
- [Documentation](https://adguard.com/ru/adguard-home/overview.html)

## Автоматизация

Автоматизацией можно вынести стартовые файлы сервиса и включить его:

```bash
uv run router deploy run adguard
uv run router sync pull adguard
uv run router sync push adguard
```

Что делает автоматизация:
- деплоит стартовые файлы из `init/_System/adGuardHome`
- копирует скрипт `init/data/services/adguardhome.sh`
- скачивает бинарь `AdGuardHome` нужной версии, если на роутере его еще нет или версия отличается
- синхронизирует service-specific файлы через `sync/`

Что она не делает:
- не меняет за вас системный `/etc/config/dhcp`
- не выполняет все дополнительные системные UCI-правки
- не заменяет ручную настройку самого AdGuard через Web UI

Примеры системных правок лежат в `init/etc/config/*`, но применять их все так же нужно вручную и осознанно.

## Установка

Сделано на основе инструкции из [тг](https://t.me/xiaomi_be7000/12423) (от @T7m):

1. Указать версию в `config.yml`:

    ```yaml
    services:
      adguard:
        enabled: true
        version: 0.107.74
    ```

   После этого `uv run router deploy run adguard` сам скачает и выложит нужный бинарь `AdGuardHome`.

   Если хотите сделать это вручную, тогда можно скачать пакет с <https://github.com/AdguardTeam/AdGuardHome/releases>:

    ```bash
    export ADGUARDHOME_VERSION=0.107.73
    wget -qO- "https://github.com/AdguardTeam/AdGuardHome/releases/download/v${ADGUARDHOME_VERSION}/AdGuardHome_linux_arm64.tar.gz" | tar -xzf - -C ./tmp
    ```

2. На внешнем накопителе в папке `System` создать подпапку `adGuardHome` (тут будут храниться все необходимое для adguard home) и пару системных папок:

    ```bash
    cd ${ROUTER_USB_DIR}/System
    mkdir -p adGuardHome/usr/bin
    ```

3. Копируем туда на систему сам бинарь и необходимые конфиги.

   Если делать вручную по новой структуре репозитория:

    ```bash
    scp -O tmp/AdGuardHome/AdGuardHome root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/adGuardHome/usr/bin/AdGuardHome
    scp -O -r init/_System/adGuardHome/etc root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/adGuardHome
    ```

   Либо используем `uv run router deploy run adguard`.

4. Скопировать сам скрипт запуска adguardhome (и убедитесь что в общем скрипте `/data/startup.sh` включен запуск этого скрипта):

    ```bash
    scp -O init/data/services/adguardhome.sh root@${ROUTER_ADDRESS}:/data/services/adguardhome.sh
    scp -O init/data/startup.sh root@${ROUTER_ADDRESS}:/data/startup.sh
    ```

5. Далее конфигурируем DNS на роутере согласно [инструкции](https://openwrt.org/docs/guide-user/services/dns/adguard-home) и делаем все по шагам начиная с секции Setup и ниже. Рекомендуется сохранить бекап перед началом. Из основного:

    ```bash
    cd /etc/config

    # Делаем локальный бекап, но лучше сохраните себе еще куда-нибудь
    # (особенно интересуют разделы dnsmasq, dhcp 'lan', dhcp 'guest')
    cp dhcp dhcp.bak

    # Меняем сам конфиг (команды изменены, чтобы у нас все работало)
    dev=$(ifstatus lan | grep \"device | awk '{ print $2 }' | sed 's/[",]//g')
    NET_ADDR=$(ip -o -4 addr list $dev | awk 'NR==1{ split($4, ip_addr, "/"); print ip_addr[1]; exit }')
    NET_ADDR6=$(ip -o -6 addr list $dev scope global | awk '$4 ~ /^fd|^fc/ { split($4, ip_addr, "/"); print ip_addr[1]; exit }')
    echo "Router IPv4 : ""${NET_ADDR}"
    echo "Router IPv6 : ""${NET_ADDR6}"

    uci set dhcp.@dnsmasq[0].port="0"
    uci set dhcp.@dnsmasq[0].domain="lan"
    uci set dhcp.@dnsmasq[0].local="/lan/"
    uci set dhcp.@dnsmasq[0].expandhosts="1"
    uci set dhcp.@dnsmasq[0].cachesize="0"
    uci set dhcp.@dnsmasq[0].noresolv="1"
    uci -q del dhcp.@dnsmasq[0].server

    uci -q del dhcp.lan.dhcp_option
    uci -q del dhcp.lan.dns

    uci add_list dhcp.lan.router="${NET_ADDR}"
    uci add_list dhcp.lan.dns1="${NET_ADDR}"
    uci commit dhcp
    ```

6. Тестируем запуск:

    ```bash
    service dnsmasq restart
    service odhcpd restart
    /data/startup.sh
    # Возможно потребуется ребут роутера
    ```

7. После старта сервиса в `/etc/adguardhome.yaml` конфигурируем:

    ```yaml
    ...
    log:
        enabled: true
        file: "/data/usr/log/adguardhome/adguard.log"
        max_backups: 3
        max_size: 100
        max_age: 7
        compress: false
        local_time: true
        verbose: false
    ...
    ```

## Настройка

Все в дальнейшем настраивается через Web UI на порте **3000** (например, <http://192.168.31.1:3000>). Тут в основном рекомендации, настраивать нужно под себя.

1. Во вкладке **Настройки** -> **Настройки DNS** ставим необходимые DNS сервера. Можно воспользоваться следующим примером (раскомментируйте необходимое), при этом часть DNS серверов доступно только через VPN, поэтому они ожидаемо без него не заработают (настройте доступ к ним в v2ray) -> [файл](examples/dns_servers.txt). Там же включаем "Параллельные запросы", чтобы было быстрее.
2. Там же прописать **Bootstrap DNS-серверы**:

    ```txt
    77.88.8.8
    77.88.8.1
    89.207.216.1
    95.131.144.199
    ```

3. В одном из DNS выше прописан пример использования вашего личного DNS в AdGuard. Рекомендуется его создать. Все это можно сделать на сайте <https://adguard-dns.io/ru/dashboard/> после регистрации.
4. Также на этой вкладке **Настройки** -> **Настройки DNS** нужно выключить обработку IPv6.
5. Во вкладке **Фильтры** -> **Черные списки DNS** выставляем следующие фильтры:
   - **AdGuard DNS filter**
   - **HaGeZi's Normal Blocklist**
   - **AdGuard DNS Popup Hosts filter**
6. Во вкладке **Фильтры** -> **Заблокированные сервисы** выключаем нужные приложения (например, **Max**)
7. Во вкладке **Фильтры** -> **Перезапись DNS запросов** создать имя для своего сервера, чтобы ходить на него не по IP адресу, а по "слову". Также делаем это, чтобы все сервисы были доступны по удобным DNS именам:
   1. `router.lan` -> `192.168.31.1`
   2. `router` -> `router.lan`
   3. `adguard.lan` -> `192.168.31.1`
   4. `adguard` -> `adguard.lan`
   5. `v2raya.lan` -> `192.168.31.1`
   6. `v2raya` -> `v2raya.lan`
8. Сначала в роутере (вкладка **Settings** -> **LAN Settings** -> **DHCP static IP assignment**) проставьте статику для большинства ваших устройств, а после в AdGuardHome во вкладке **Настройки** -> **Настройки клиентов** также их пропишите. Позволит вам проще видеть кто и зачем обращается.

   Если хотите делать это через CLI, теперь можно точечно управлять DHCP host entries так:

    ```bash
    uv run router dhcp hosts
    uv run router dhcp add my_device aa:bb:cc:dd:ee:ff 192.168.31.50
    uv run router dhcp remove aa:bb:cc:dd:ee:ff --by mac
    ```

## Обновление

Для обновления - просто обновите нужные вам компоненты в директории `${ROUTER_USB_DIR}/System/adGuardHome`. В том числе именно таким образом следует обновлять бинарь adguard.

А для получение актуальных `etc` конфигов - взять пакет `adguardhome_0.107.57-r1_aarch64_generic.ipk` с сайта <https://archive.openwrt.org/releases/24.10.0-rc1/packages/aarch64_generic/packages/>. `ipk` переименовать в `tar.gz`. Распаковать этот архив. Достать из распакованных данных новый архив - `data.tag.gz`, его тоже распаковать и получим необходимую папку `data`. В ней подправить нужные конфиги и можно обновляться.

## Удаление

В целом все компоненты сервисы состоят из:
1. Директории `${ROUTER_USB_DIR}/System/adGuardHome` - ее можно просто удалить с помощью `rm -rf <dir>`
2. Множества симлинков в разных местах, но они будут стерты/бесполезны при перезапуске роутера
3. Запуска самого компоненты в `/data/startup.sh`
4. Скрипта запуска в `/data/services/adguardhome.sh`

Поэтому удалив это - вы удалите сервис.

## Дополнительно

### Работа с сервисом

Через команду `service adguardhome help` и подобные команды

### Бекап

#### Настройки сервиса

Можно забекапить путем сохранения файла - `${ROUTER_USB_DIR}/System/adGuardHome/adguardhome.yaml`. Скопировать себе на систему можно следующим образом:

```bash
mkdir -p sync/etc
scp -O root@${ROUTER_ADDRESS}:/etc/adguardhome.yaml sync/etc/adguardhome.yaml
```

Либо использовать:

```bash
uv run router sync pull adguard
```

#### Настройки dhcp

Дефолтный файл сохранен в файле `/etc/config/dhcp.bak` (если вы делали согласно этой инструкции), а также выглядит примерно как в [файле](examples/adguard_dhcp.bak)
