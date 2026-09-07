# syntax=docker/dockerfile:1

FROM alpine:3.22

ARG FRP_VERSION=0.71.0
ARG TARGETARCH

RUN set -eux; \
    apk add --no-cache ca-certificates python3 wget tar; \
    case "$TARGETARCH" in \
      amd64) FRP_ARCH=amd64 ;; \
      arm64) FRP_ARCH=arm64 ;; \
      arm) FRP_ARCH=arm ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    wget -qO /tmp/frp.tar.gz "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_${FRP_ARCH}.tar.gz"; \
    tar -xzf /tmp/frp.tar.gz -C /tmp; \
    install -m 0755 "/tmp/frp_${FRP_VERSION}_linux_${FRP_ARCH}/frpc" /usr/local/bin/frpc; \
    rm -rf /tmp/frp*; \
    frpc --version

COPY entrypoint.py /usr/local/bin/frpc-entrypoint
RUN chmod +x /usr/local/bin/frpc-entrypoint

WORKDIR /app

ENTRYPOINT ["/usr/local/bin/frpc-entrypoint"]
