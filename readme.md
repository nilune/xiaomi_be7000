# XIAOMI BE7000

Практическая инструкция по подготовке роутера Xiaomi BE7000 и управлению его сервисами.

> Все команды ниже запускайте либо на роутере, либо из корня этого репозитория.

В документации используются общие переменные (поменяйте их согласно вашим настройкам):

```bash
export ROUTER_ADDRESS=192.168.31.1
export ROUTER_USB_DIR=/mnt/usb-ef8d1024
```

- [Установка (база)](#установка-база)
- [Установка (enodia)](#установка-enodia)
- [Полезное](#полезное)
  - [Бекап и как его делать](#бекап-и-как-его-делать)
  - [Выключение ненужных wifi сетей](#выключение-ненужных-wifi-сетей)
- [Важные файлы и полезные команды](#важные-файлы-и-полезные-команды)
- [Задачи](#задачи)

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

## Установка (enodia)

См. [enodia-setup](./enodia-setup/)

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
