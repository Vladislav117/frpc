# frpc

Docker-образ для запуска клиента [FRP](https://github.com/fatedier/frp) с простым JSON-конфигом.

При запуске контейнер читает `/app/frpc.json`, подставляет переменные окружения, создаёт TOML-конфиг и запускает `frpc`.

## Пример конфигурации и compose.yml

- [frpc.json](example/frpc.json)
- [compose.yml](example/compose.yml)
