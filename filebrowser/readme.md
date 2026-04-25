# FileBrowser

Доступ к файлам и данным через браузер

Ссылки:

- [Github](https://github.com/filebrowser/filebrowser)
- [Documentation](https://filebrowser.org/index.html)

## Установка

docker run -d \
  --name filebrowser \
  -p 8088:80 \
  -v /etc/config:/srv/etc/config \
  -v /mnt:/srv/mnt \
  --restart unless-stopped \
  filebrowser/filebrowser

  -v /opt/filebrowser/database.db:/database.db \
  -v /opt/filebrowser/settings.json:/config/settings.json \