# FileBrowser

Веб-интерфейс для управления файлами на роутере через браузер.

## Ссылки

- [GitHub](https://github.com/filebrowser/filebrowser)
- [Документация](https://filebrowser.org/)

## Автоматизация

Теперь сервис участвует в общей модели `init + sync`:

```bash
uv run router deploy run filebrowser
uv run router sync pull filebrowser
uv run router sync push filebrowser
```

При деплое создаются и используются:
- `init/_System/filebrowser/etc/nginx/conf.d/filebrowser.conf`
- `${ROUTER_USB_DIR}/System/filebrowser/config`
- `${ROUTER_USB_DIR}/System/filebrowser/database`
- `/data/services/filebrowser.sh`

То есть конфиг, база и стартовый скрипт становятся перманентными, а не живут только внутри контейнера.

## Установка

### 1. Настройка config.yml

```yaml
services:
  filebrowser:
    enabled: true
    port: 8088
    initial_username: admin
    initial_password: admin
    sources:
      - path: /mnt/usb-ef8d1024
        name: USB Drive
      - path: /etc/config
        name: Router Config
      - path: /data
        name: Router Data
```

### 2. Запуск через Deployer

```bash
uv run router deploy run filebrowser
```

На первом запуске будет создан пользователь с логином `admin` и паролем `admin`, если база еще не существует. После этого пароль нужно сразу сменить через UI. Дальше он уже хранится в персистентной базе `${ROUTER_USB_DIR}/System/filebrowser/database/filebrowser.db`.

### 3. Ручной запуск через Docker

```bash
${ROUTER_USB_DIR}/mi_docker/docker-binaries/docker run -d \
  --name filebrowser \
  -p 8088:80 \
  -v /etc/config:/srv/etc_config \
  -v /mnt:/srv/mnt \
  -v /data:/srv/data \
  --restart unless-stopped \
  filebrowser/filebrowser:latest
```

## Доступ

После запуска откройте в браузере:

```txt
http://${ROUTER_ADDRESS}:8088
```

Дефолтные credentials:
- Логин: `admin`
- Пароль: `admin`

**Важно:** Сразу поменяйте пароль после первого входа.

## Конфигурация

### Монтируемые директории

Каждая директория в `sources` монтируется в контейнер:

| Путь на роутере | Путь в контейнере | Описание |
|-----------------|-------------------|----------|
| `/mnt/usb-ef8d1024` | `/srv/usb_drive` | Внешний USB накопитель |
| `/etc/config` | `/srv/etc_config` | Конфигурация роутера |
| `/data` | `/srv/data` | Данные и скрипты |

### Порты

- `port` - порт веб-интерфейса (по умолчанию 8088)

### Персистентные данные

- `${ROUTER_USB_DIR}/System/filebrowser/config` - runtime config
- `${ROUTER_USB_DIR}/System/filebrowser/database` - база пользователей и настроек
- `${ROUTER_USB_DIR}/System/filebrowser/etc/nginx/conf.d/filebrowser.conf` - nginx proxy config

Это же участвует в `sync pull/push`.

## Полезные команды

```bash
# Проверить статус
docker ps | grep filebrowser

# Посмотреть логи
docker logs filebrowser

# Перезапустить
docker restart filebrowser

# Остановить
docker stop filebrowser

# Удалить контейнер
docker rm filebrowser
```

## Безопасность

1. Обязательно смените дефолтный пароль
2. Не открывайте порт наружу без необходимости
3. Ограничьте доступ через firewall при необходимости
