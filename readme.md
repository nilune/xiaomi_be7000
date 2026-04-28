# XIAOMI BE7000

Практическая инструкция по подготовке роутера Xiaomi BE7000 и управлению его сервисами.

> Все команды ниже запускайте либо на роутере, либо из корня этого репозитория.

В документации используются общие переменные (поменяйте их согласно вашим настройкам):

```bash
export ROUTER_ADDRESS=192.168.31.1
export ROUTER_USB_DIR=/mnt/usb-ef8d1024
```

- [Структура репозитория](#структура-репозитория)
- [Установка (база)](#установка-база)
- [Установка (работа с сервисами)](#установка-работа-с-сервисами)
- [Автоматизация (Deployer)](#автоматизация-deployer)
  - [Установка](#установка)
  - [Основные команды](#основные-команды)
- [Полезное](#полезное)
  - [Бекап и как его делать](#бекап-и-как-его-делать)
  - [Выключение ненужных wifi сетей](#выключение-ненужных-wifi-сетей)
  - [Донастройка IoT сети](#донастройка-iot-сети)
  - [Настройка статических адресов](#настройка-статических-адресов)
- [Важные файлы и полезные команды](#важные-файлы-и-полезные-команды)
- [Задачи](#задачи)

## Структура репозитория

Текущая структура после переработки такая:

- `doc/` — вся документация по сервисам и примеры
- `init/` — стартовые файлы, которые можно безопасно раскатывать на роутер
- `sync/` — локальная синхронизация фактического состояния роутера, не коммитится
- `src/` — CLI-утилита для deploy/sync/DHCP

Основные сервисные документы:
- [Core](doc/core.md)
- [AdGuard Home](doc/adguard.md)
- [V2rayA](doc/v2raya.md)
- [FileBrowser](doc/filebrowser.md)
- [Примеры](doc/examples)

Важно:
- изменения в системных `/etc/config/dhcp`, `/etc/config/firewall`, `/etc/config/network`, `/etc/config/wireless` по-прежнему считаются ручным шагом
- `init/etc/config/*` содержит примеры и заготовки, а не файлы для безусловного автоматического применения

## Установка (база)

> Сделано на основе 1-4 пунктов из [статьи на 4pda](https://4pda.to/forum/index.php?showtopic=1070166&view=findpost&p=131597534).

1. Настраиваем ssh к роутеру с помощью [xmir-patcher](https://github.com/openwrt-xiaomi/xmir-patcher.git) (также смотри [инструкцию](https://4pda.to/forum/index.php?showtopic=1070166&view=findpost&p=131157661)):
   1. `git clone https://github.com/openwrt-xiaomi/xmir-patcher.git`
   2. (опционально, если нужен новый python) ставим через `uv`:

        ```bash
        uv venv --python 3.13
        source .venv/bin/activate
        ```

   3. (опционально, в случае ошибок) пофиксить на macOS согласно [гайду](https://github.com/openwrt-xiaomi/xmir-patcher/issues/115#issuecomment-3353355239):

        ```bash
        brew install libssh2
        BREW_LIB="$(brew --prefix libssh2)/lib/libssh2.1.dylib"
        ls -l "$BREW_LIB"

        PKG_DIR="CHANGEME/venv/lib/CHANGEME/site-packages/ssh2"

        cp "$BREW_LIB" "$PKG_DIR/libssh2.1.dylib"

        xattr -dr com.apple.quarantine "$PKG_DIR/libssh2.1.dylib" || true

        for so in "$PKG_DIR"/*.so; do
            echo "Patching $so"
            install_name_tool -change @rpath/libssh2.1.dylib @loader_path/libssh2.1.dylib "$so"
        done
        ```

   4. `./run.sh`
      1. Выбираем **1**, ставим IP адрес
      2. Выбираем **2**, делаем эксплойт
      3. Выбираем **5**, ставим язык
      4. Выбираем **6**, ставим ssh доступ
      5. Выходим с помощью **0**
2. Подключаем небольшую (но желательно быструю) внешнюю флешку / microSD (но на ней должно быть 32GB+, поэтому рекомендуется брать 64GB). Включаем виртуальную память и docker согласно [инструкции](https://post.smzdm.com/p/akk9nvv8/). Вкратце:
    1. Форматируем нашу флешку под ext4, на macOS согласно [инструкции](https://gist.github.com/kephircheek/31e8c62ca0ffe424c767f9290f563379):

        ```bash
        diskutil list
        diskutil unmountDisk disk4
        brew install e2fsprogs
        sudo $(brew --prefix e2fsprogs)/sbin/mkfs.ext4 /dev/disk4
        sudo $(brew --prefix e2fsprogs)/sbin/e2label /dev/disk4 "Router System"
        ```

    2. Вставляем флешку и через UI включаем виртуальную память
    3. Устанавливаем docker - просто все кнопки по очереди. Потом заходим в UI и меняем пароль (дефолтный логин-пароль - `admin:admin`; менять через кнопку замочка сверху справа)
    4. Убираем аутентификацию для docker согласно [инструкции](https://4pda.to/forum/index.php?showtopic=1070166&view=findpost&p=131213506). То есть делаем:
        1. Создаем файл `/etc/crontabs/patches/disable_opa.sh`:

            ```txt
            #!/bin/sh
            #date +%H:%M:%S > /tmp/timestamp_opa
            cp /tmp/run/docker/opa/authz.rego /tmp/run/docker/opa/authz.rego.bak
            rm /tmp/run/docker/opa/authz.rego
            settings="package docker.authz
            default allow = true"
            echo "$settings" > /tmp/run/docker/opa/authz.rego
            ```

        2. В файле `/etc/crontabs/root` в конце добавляем:

            ```txt
            # Disable docker auth
            */1 * * * * /etc/crontabs/patches/disable_opa.sh >/dev/null 2>&1
            ```

3. (опционально, требует ресурсов) Ставим первый сервис - `portrainer` - позволяет легко управлять контейнерами (вместо дефолтного, так как он не удобен). Сам сервис будет доступен в UI по адресу <http://${ROUTER_ADDRESS}:9000>. Заходим по ssh на роутер и запускаем на нем (поменяй путь согласно твоему имени флешки):

    ```bash
    ${ROUTER_USB_DIR}/mi_docker/docker-binaries/docker run \
        -d \
        -p 9000:9000 \
        -p 9443:9443 \
        --name portainer \
        --restart=always \
        -v /var/run/docker.sock:/var/run/docker.sock \
        portainer/portainer-ce:latest
    ```

## Установка (работа с сервисами)

Тут прописаны общие шаги, которые нужно сделать перед установкой сервисов.

Сама настройка:

1. На внешнем накопителе создать папку `System` - в ней будут устанавливаться все необходимые зависимости для устанавливаемых утилит.
2. В директории `/data` выполнить следующее:
   1. Создать директорию `services`, в которой будут находится все скрипты для запуска конкретных сервисов:

      ```bash
      mkdir -p /data/services
      ```

   2. Скопировать в нее скрипт `startup.sh`:

      ```bash
      uv run router deploy run startup
      ```

   3. При необходимости поправить `USB_DIR` в `init/data/startup.sh` под ваш путь к внешнему накопителю
   4. При необходимости включить или отключить отдельные вызовы в функции `do_startup`
   5. Также создать директорию `scripts` для дополнительных скриптов:

      ```bash
      mkdir -p /data/scripts
      ```

3. В `/etc/config/firewall` добавить в самом конце следующее (это позволит запускать скрипт `/data/startup.sh` при каждом включение роутера):

    ```txt
    config include 'startup'
        option type 'script'
        option path '/data/startup.sh'
        option enabled '1'
    ```

4. Дальше переходите к нужному сервису и настраивайте его по профильной инструкции:
   1. [Core](doc/core.md) - специальная настройка для кастомизации системных настроек
   2. [AdGuard Home](doc/adguard.md) - настройка DNS через AdGuardHome
   3. [V2rayA](doc/v2raya.md) - настройка прокси через V2rayA и Xray
   4. [FileBrowser](doc/filebrowser.md) - настройка доступа к данным через браузер

## Автоматизация (Deployer)

CLI-утилита для управления конфигурацией роутера:
- управлять статическими IP адресами напрямую через `/etc/config/dhcp`
- показывать кандидатов на перевод в статику по текущим DHCP lease-записям
- синхронизировать конфигурации между роутером и локальной директорией `sync/`
- деплоить базовый `startup.sh` и файлы сервисов из `init/`
- скачивать и обновлять версии бинарей `adguard`, `v2raya` и `xray` по `config.yml`

### Установка

```bash
uv sync
cp .env.example .env
cp config.yml.example config.yml
```

В `.env` должен быть `ROUTER_SSH_PASSWORD`.

### Основные команды

```bash
uv run router config validate              # Проверка соединения
uv run router config show

# DHCP и статические IP
uv run router dhcp leases                  # Текущие аренды
uv run router dhcp hosts                   # Текущие статические хосты
uv run router dhcp candidates              # Кто еще не закреплен статикой
uv run router dhcp add my_device aa:bb:cc:dd:ee:ff 192.168.31.80
uv run router dhcp remove aa:bb:cc:dd:ee:ff --by mac

# Синхронизация
uv run router sync pull --all
uv run router sync pull adguard
uv run router sync push dhcp --dry-run
uv run router sync push v2raya

# Deploy
uv run router deploy run --dry-run
uv run router deploy run
uv run router deploy run startup
uv run router deploy run base              # Алиас для startup
uv run router deploy run adguard
uv run router deploy run filebrowser
```

Что важно понимать:
- `sync/` не коммитится и отражает фактическое состояние роутера
- `init/` хранит стартовые файлы для первоначального включения сервисов
- `uv run router deploy run` без аргументов сначала выкладывает `startup.sh`, затем все сервисы с `enabled: true` в `config.yml`
- `enabled: false` теперь приводит к реальному отключению сервиса без удаления его данных
- изменения в системных `/etc/config/*` все еще предполагают ручной контроль
- `filebrowser` теперь хранит базу и конфиг в `${ROUTER_USB_DIR}/System/filebrowser`, а не только внутри контейнера
- docker-сервисы не запускаются из `startup.sh`: они поднимаются напрямую через `docker run --restart unless-stopped`
- `filebrowser` в текущей схеме запускается с `--user 0:0`, потому что встроенный пользователь image не смог писать в bind-mounted каталог базы на роутере

Минимальный пример версий в `config.yml`:

```yaml
services:
  adguard:
    enabled: true
    version: 0.107.74

  v2raya:
    enabled: true
    version: 2.2.7.5
    xray_version: 26.4.15

  filebrowser:
    enabled: true
    version: latest
```

Подробнее о внутреннем устройстве см. в [ARCHITECTURE.md](ARCHITECTURE.md).

## Полезное

### Бекап и как его делать

1. Базовые ваши настройки: скриншоты и дубли любых файлов, которые вам важны и нужны
2. Общие настройки роутера: на web странице роутера на странице **Settings** -> **System Settings** есть бекап настроек и их восстановление
3. Вся система: с помощью `xmir-patcher`
4. Для рабочей синхронизации конфигов теперь используйте `uv run router sync pull ...`, результат будет складываться в `sync/`

### Выключение ненужных wifi сетей

Согласно комментарию на [4pda](https://4pda.to/forum/index.php?showtopic=1070166&view=findpost&p=130785221) выключаем ненужные wifi сетей в файле `/etc/config/wireless`:
1. вредная `miaiot` сеть от xiaomi: у `config wifi-iface 'miot_2G'` выставляем `option disabled '1'`
2. `mesh` виртуальную сеть: у `config wifi-iface 'bh_ap'` выставляем `option disabled '1'`
3. `guest / iot` сети если вам не нужен какой-то из диапазонов (например 2G или 5G): также выставляем `option disabled '1'` в необходимых местах

### Донастройка IoT сети

По дефолту IoT сеть находится в LAN и в ней все равно нельзя настраивать статические адреса, поэтому появилось желание перенести эту сеть в уже созданную отдельную `miot` сеть на адресах `192.168.32.*` и как внутри прописать статику:
1. Включаем в приложении Xiaomi саму IoT сеть
2. В файле `/etc/config/wireless` ставим следующие опции в соответствующем разделе:

    ```txt
    config wifi-iface 'iot_2g'
        option network 'miot'

    config wifi-iface 'iot_5g'
        option network 'miot'
    ```

3. В файле `/etc/config/firewall` добавляем (настройка для **xray** нужна только если вы настраивали **v2raya** на роутере):

    ```txt
    config zone 'miot_zone'
        option name 'miot'
        option network 'miot'
        option input 'REJECT'
        option forward 'REJECT'
        option output 'ACCEPT'

    config rule 'miot_xray'
        option name 'Allow MIOT to Xray TPROXY'
        option src 'miot'
        option proto 'tcpudp'
        option mark '0x40/0xc0'
        option target 'ACCEPT'

    config rule 'miot_dns'
        option name 'Allow MIOT DNS Queries'
        option src 'miot'
        option dest_port '53'
        option proto 'tcpudp'
        option target 'ACCEPT'

    config rule 'miot_dhcp'
        option name 'Allow MIOT DHCP request'
        option src 'miot'
        option src_port '67-68'
        option dest_port '67-68'
        option proto 'udp'
        option target 'ACCEPT'
    ```

    И убираем (или просто комментируем):

    ```txt
    config include 'miot'
        option type 'script'
        option path '/lib/firewall.sysapi.loader miot'
        option enabled '1'
        option reload '1'
    ```

4. В файле `/etc/config/dhcp` ставим следующие опции в соответствующем разделе:

    ```txt
    config dhcp 'miot'
        option leasetime '12h'
        option ra_default '1'
        option ra 'server'
        option ra_preference 'high'
        option ra_maxinterval '20'
        option ra_lifetime '1800'
        list ra_flags 'managed-config'
        list ra_flags 'other-config'
        option router '192.168.32.1'
        option dns1 '192.168.32.1'
    ```

5. В файле `/etc/config/network` ставим следующие опции в соответствующем разделе:

    ```txt
    config interface 'miot'
        option bridge_empty '1'
    ```

TODO: доступ через firewall с определенных адресов к samba на роутере или в целом ко всему

### Настройка статических адресов

Статические IP адреса теперь настраиваются либо:
- точечно через `router dhcp add/remove`
- через просмотр кандидатов командой `router dhcp candidates`
- вручную через UCI на роутере
- либо через ручное редактирование `sync/etc/config/dhcp` с последующим `sync push`

Быстрый старт через CLI:

```bash
uv run router dhcp hosts
uv run router dhcp candidates
uv run router dhcp add my_device aa:bb:cc:dd:ee:ff 192.168.1.100
uv run router dhcp remove my_device --by name
```

Если какие-то устройства не должны попадать в список кандидатов, добавьте исключения в `config.yml`:

```yaml
dhcp:
  static_candidates:
    exclude_macs:
      - "aa:bb:cc:dd:ee:ff"
    exclude_mac_prefixes:
      - "ec:fa:bc"
```

Если хотите работать через pull/push модель:

```bash
uv run router sync pull dhcp
# редактируем sync/etc/config/dhcp
uv run router sync push dhcp
```

Вручную через UCI на роутере:

```bash
# Добавить статический хост
uci set dhcp.my_device=host
uci set dhcp.my_device.mac='aa:bb:cc:dd:ee:ff'
uci set dhcp.my_device.ip='192.168.1.100'
uci set dhcp.my_device.name='my_device'
uci commit dhcp
service dnsmasq restart
```

## Важные файлы и полезные команды

1. `/etc/config/network` - все сети на роутере (в том числе `docker`, `lan`, `guest`)
2. `/etc/config/wireless` - wifi сети и их настройка
3. `/etc/config/firewall` - правила firewall между сетями, и, как ни странно, именно тут вызываются начальные скрипты настройки вашей ОС с помощью хака
4. `/etc/config/dhcp` - настройка dhcp, тут можно вручную прописывать статику. Дополнительно:
   - `/tmp/dhcp.leases` - в этом файле все временно выданные IP адреса (не статика)
   - `/etc/init.d/dnsmasq restart` - команда для применения конфига после изменений
   - `uci` - утилита для обновления конфига через консоль
5. `/etc/config/samba` и `/etc/samba/smb.conf` - настройки `samba`
6. `iptables -t mangle -L -n -v` - списки `iptables` для трафика
7. `netstat -ntplu` - открытые слушающие порты
8. `sync/` - локальная рабочая копия актуальных конфигов и файлов роутера
9. `init/` - стартовые файлы, которые используются для первичной раскатки сервисов

## Задачи

- [ ] Пофиксить права доступа на внешней флешке, чтобы можно подключаться через smb
- [ ] Работа с диском
- [ ] https://post.smzdm.com/p/akk9nvv8/ - home assistant и прочее
- [ ] подготовить готовые скрипты создания бекапа и восстановления из него
- [ ] улучшить все конфиги с помощью ИИ агента, сделать автоматизацию раскатки
