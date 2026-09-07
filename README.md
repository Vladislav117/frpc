# frpc

Docker-образ для запуска клиента [FRP](https://github.com/fatedier/frp) с простым JSON-конфигом.

При запуске контейнер читает `/app/frpc.json`, подставляет переменные окружения, создаёт TOML-конфиг и запускает `frpc`.

## Пример конфигурации и compose.yml

`frpc.json`:

```json
{
    "frp": {
        "server": "proxy.example.com:7000",
        "token": "${FRP_TOKEN}"
    },
    "routes": [
        {
            "type": "TCP",
            "target": "server:5000",
            "port": 5000
        },
        {
            "type": "UDP",
            "target": "server:5001",
            "port": 5001
        },
        {
            "type": "HTTP",
            "target": "frontend:3000",
            "domains": [
                "test.example.com"
            ]
        }
    ]
}
```

`compose.yml`:

```yaml
services:
  # TCP at 5000 and UDP at 5001
  server:
    image: ???

  # HTTP at 3000
  frontend:
    image: ???

  frpc:
    image: ghcr.io/vladislav117/frpc:latest
    restart: unless-stopped
    environment:
      FRP_TOKEN: ${FRP_TOKEN}
    volumes:
      - ./frpc.json:/app/frpc.json:ro
```
