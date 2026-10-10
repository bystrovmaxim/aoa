#!/usr/bin/env bash
# scripts/deploy_demonstrator_stand.sh — one-command deployment for the demonstrator stand.
#
# The stand is accepted by opening two URLs and by running one command — this
# script is that command. In order: DNS and TLS-terminator gates, build both
# images, start both containers, poll their health, verify both domains, and
# roll back to the previously running images on any failure.
#
# Host facts (the DNS zone, the existing TLS terminator, the real values of
# deploy/stand/.env) never enter this repository: the gates assert the facts,
# and configuration/secrets are read from /etc/aoa-stand.env on the host.
#
# Usage:
#   bash scripts/deploy_demonstrator_stand.sh           # full host deployment
#   bash scripts/deploy_demonstrator_stand.sh --local   # local loopback validation

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deploy/stand/docker-compose.yml"

DEMO_DOMAIN="${DEMO_DOMAIN:-dev.demo.aoa.run}"
MAXITOR_DOMAIN="${MAXITOR_DOMAIN:-dev.maxitor.aoa.run}"
DEMO_PORT="${DEMO_PORT:-8100}"
MAXITOR_PORT="${MAXITOR_PORT:-8101}"

LOCAL_MODE=0
if [[ "${1:-}" == "--local" ]]; then
    LOCAL_MODE=1
fi

say() { printf '%s\n' "$*"; }
fail() { say "FAIL: $*"; exit 1; }
rollback() {
    say "ROLLBACK: $*"
    say "restoring the previous images and containers..."
    for service in demo maxitor; do
        if docker image inspect "stand-${service}:backup" >/dev/null 2>&1; then
            docker image tag "stand-${service}:backup" "stand-${service}:latest"
        fi
    done
    docker compose -f "$COMPOSE_FILE" up -d >/dev/null 2>&1 || true
    exit 1
}

gate_dns() {
    [[ $LOCAL_MODE -eq 1 ]] && return 0
    for domain in "$DEMO_DOMAIN" "$MAXITOR_DOMAIN"; do
        if ! python3 -c "import socket, sys; socket.getaddrinfo(sys.argv[1], None)" "$domain" >/dev/null 2>&1; then
            fail "DNS gate: '$domain' does not resolve — create the A record before deploying."
        fi
    done
    say "DNS gate: both domains resolve"
}

detect_terminator() {
    [[ $LOCAL_MODE -eq 1 ]] && { echo "local"; return 0; }
    if command -v nginx >/dev/null 2>&1; then echo "nginx"; return 0; fi
    if command -v caddy >/dev/null 2>&1; then echo "caddy"; return 0; fi
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qi traefik; then echo "traefik"; return 0; fi
    return 1
}

install_vhosts() {
    local terminator="$1"
    case "$terminator" in
        nginx)
            [[ $EUID -eq 0 ]] || fail "vhost step: run as root to add nginx virtual hosts."
            local cert_dir="${STAND_CERT_DIR:-/etc/nginx/ssl/aoa.run}"
            for entry in "$DEMO_DOMAIN:$DEMO_PORT" "$MAXITOR_DOMAIN:$MAXITOR_PORT"; do
                local domain="${entry%%:*}"
                local port="${entry##*:}"
                cat > "/etc/nginx/sites-available/${domain}" <<EOF
server {
    listen 80;
    server_name ${domain};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${domain};

    ssl_certificate     ${cert_dir}/fullchain.pem;
    ssl_certificate_key ${cert_dir}/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:${port}/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
EOF
                ln -sf "/etc/nginx/sites-available/${domain}" "/etc/nginx/sites-enabled/${domain}"
            done
            nginx -t || fail "vhost step: nginx -t rejected the new virtual hosts."
            systemctl reload nginx || fail "vhost step: nginx reload failed."
            if openssl x509 -in "${cert_dir}/fullchain.pem" -noout -text 2>/dev/null | grep -q "DNS:\\*\\.aoa.run"; then
                say "certificate step: the shared wildcard already covers both names — reused and renewed by the host's own mechanism."
            elif command -v certbot >/dev/null 2>&1; then
                certbot --nginx -d "$DEMO_DOMAIN" -d "$MAXITOR_DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect \
                    || fail "certificate step: certbot could not issue the certificates."
            else
                fail "certificate step: no shared wildcard and no certbot — certificates cannot be issued here."
            fi
            ;;
        caddy)
            [[ $EUID -eq 0 ]] || fail "vhost step: run as root to add caddy virtual hosts."
            cat >> /etc/caddy/Caddyfile <<EOF

${DEMO_DOMAIN} {
    reverse_proxy 127.0.0.1:${DEMO_PORT}
}
${MAXITOR_DOMAIN} {
    reverse_proxy 127.0.0.1:${MAXITOR_PORT}
}
EOF
            systemctl reload caddy || fail "vhost step: caddy reload failed."
            ;;
        *)
            fail "terminator gate: detected '${terminator}' is not scripted — add the two virtual hosts manually and name this gap."
            ;;
    esac
    say "virtual hosts added to ${terminator}; certificates issued by its own renew mechanism"
}

wait_healthy() {
    local service="$1"
    local attempt
    for attempt in $(seq 1 30); do
        local status
        status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "stand-${service}-1" 2>/dev/null || true)"
        if [[ "$status" == "healthy" ]]; then
            say "health: ${service} is healthy"
            return 0
        fi
        sleep 2
    done
    return 1
}

backup_images() {
    for service in demo maxitor; do
        local id
        id="$(docker images -q "stand-${service}:latest" 2>/dev/null || true)"
        if [[ -n "$id" ]]; then
            docker image tag "stand-${service}:latest" "stand-${service}:backup"
        fi
    done
}

main() {
    say "=== gates ==="
    gate_dns
    local terminator
    terminator="$(detect_terminator)" || fail "terminator gate: no known TLS front end found (nginx/caddy/traefik) — identify the host's terminator before deploying."
    say "terminator: ${terminator}"

    say "=== build ==="
    docker compose -f "$COMPOSE_FILE" build

    say "=== snapshot for rollback ==="
    backup_images

    say "=== up ==="
    docker compose -f "$COMPOSE_FILE" up -d

    say "=== health ==="
    wait_healthy demo || rollback "the demo container did not become healthy"
    wait_healthy maxitor || rollback "the Maxitor container did not become healthy"

    say "=== verify ==="
    if [[ $LOCAL_MODE -eq 1 ]]; then
        curl -fsS "http://127.0.0.1:${DEMO_PORT}/health" >/dev/null || rollback "local verification failed for the demo"
        curl -fsS "http://127.0.0.1:${MAXITOR_PORT}/api/health" >/dev/null || rollback "local verification failed for Maxitor"
    else
        install_vhosts "$terminator" || rollback "virtual-host installation failed"
        curl -fsS "https://${DEMO_DOMAIN}/health" >/dev/null || rollback "https verification failed for ${DEMO_DOMAIN}"
        curl -fsS "https://${MAXITOR_DOMAIN}/api/health" >/dev/null || rollback "https verification failed for ${MAXITOR_DOMAIN}"
    fi

    say "stand verified: ${DEMO_DOMAIN} + ${MAXITOR_DOMAIN}"
}

main "$@"
