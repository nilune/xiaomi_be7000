# XIAOMI BE7000

Инструкция по подготовке роутера для работы с различными компонентами (v2raya, adguardhome, прочее).

> Все команды подразумевается запускать либо с роутера, либо из этой директории (даже для любых readme во вложенных директориях).

В документации используются общие переменные (поменяйте их согласно вашим настройкам):

```bash
export ROUTER_ADDRESS=192.168.31.1
export ROUTER_USB_DIR=/mnt/usb-ef8d1024
```

- [Установка (база)](#установка-база)
- [Установка (работа с сервисами)](#установка-работа-с-сервисами)
- [Полезные](#полезные)
  - [Бекап и как его делать](#бекап-и-как-его-делать)
  - [Самые важные файлы](#самые-важные-файлы)
- [Задачи](#задачи)

## Установка (база)

> Сделано на основе 1-4 пунктов из [статьи на 4pda](https://4pda.to/forum/index.php?showtopic=1070166&view=findpost&p=131597534).

1. Настраиваем ssh к роутеру с помощью [xmir-patcher](https://github.com/openwrt-xiaomi/xmir-patcher.git) (также смотри [инструкцию](https://4pda.to/forum/index.php?showtopic=1070166&view=findpost&p=131157661):
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
    3. Устанавливаем docker - просто все кнопки по очереди. Потом заходим в UI и меняем пароль (дефолтный логин-пароль - admin:admin; менять через кнопку замочка сверху справа)
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
          scp -O startup.sh root@${ROUTER_ADDRESS}:/data
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

4. Копируем основные системные конфиги:

    ```bash
    scp -O -r core root@${ROUTER_ADDRESS}:${ROUTER_USB_DIR}/System/
    ```

5. Далее идем в интересуемые вас директории ([adguard](adguard/readme.md) или [v2raya](v2raya/readme.md)) и настраиваете согласно описанным там readme

## Полезные

### Бекап и как его делать

1. Базовые ваши настройки: скриншоты и дубли любых файлов, которые вам важны и нужны
2. Общие настройки роутера: на web странице роутера на странице **Settings** -> **System Settings** есть бекап настроек и их восстановление
3. Вся система: с помощью `xmir-patcher`

### Самые важные файлы

1. `/etc/config/firewall`
2. `/etc/config/dhcp`
3. `/etc/config/samba`
4. `/etc/config/wireless`

## Задачи

- [ ] Логи startup работают только при ручном запуске. Или как-то очень странно записываются
- [ ]
- [ ] Пофиксить права доступа на внешней флешке, чтобы можно подключаться через smb
- [ ]
- [ ] `/etc/config/wireless`
- [ ] работа с диском
- [ ] https://post.smzdm.com/p/akk9nvv8/ - home assistant и прочее
- [ ] подготовить готовые скрипты создания бекапа и восстановления из него
- [ ] улучшить все конфиги с помощью ИИ агента
