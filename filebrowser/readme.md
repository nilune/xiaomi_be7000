# FileBrowser

Веб-интерфейс для управления файлами на роутере через браузер.

## Ссылки

- [GitHub](https://github.com/filebrowser/filebrowser)
- [Документация](https://filebrowser.org/)

## Установка

### 1. Настройка config.yml

```yaml
services:
  filebrowser:
    enabled: true
    port: 8088
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

```
http://${ROUTER_ADDRESS}:8088
```

Дефолтные credentials:
- Логин: `admin`
- Пароль: `admin`

**Важно:** Сразу поменяйте пароль после первого входа!

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
