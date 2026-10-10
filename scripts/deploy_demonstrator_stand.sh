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

# Configuration and secrets live on the host, outside the repository.
if [[ -f /etc/aoa-stand.env ]]; then
    set -a
    # shellcheck disable=SC1091
    . /etc/aoa-stand.env
    set +a
fi

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
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx nginx-proxy; then echo "nginx"; return 0; fi
    if command -v nginx >/dev/null 2>&1; then echo "nginx"; return 0; fi
    if command -v caddy >/dev/null 2>&1; then echo "caddy"; return 0; fi
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qi traefik; then echo "traefik"; return 0; fi
    return 1
}

reload_nginx() {
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx nginx-proxy; then
        docker exec nginx-proxy nginx -t || fail "vhost step: nginx -t rejected the new virtual hosts."
        docker exec nginx-proxy nginx -s reload || fail "vhost step: nginx reload failed."
    else
        nginx -t || fail "vhost step: nginx -t rejected the new virtual hosts."
        systemctl reload nginx || fail "vhost step: nginx reload failed."
    fi
}

install_vhosts() {
    local terminator="$1"
    case "$terminator" in
        nginx)
            [[ $EUID -eq 0 ]] || fail "vhost step: run as root to add nginx virtual hosts."
            # The host's front end is the nginx-proxy container reading the host file
            # /root/nginx/default.conf through a read-only bind mount — edits happen on
            # the host file, and the container reloads through docker exec.
            local front_conf="${STAND_FRONT_CONF:-/root/nginx/default.conf}"
            local ssl_dir="${STAND_SSL_DIR:-/root/up2u_back/ssl}"
            local webroot="${STAND_WEBROOT:-/root/up2u_front/dist}"
            local cert_name="$DEMO_DOMAIN"
            [[ -f "$front_conf" ]] || fail "vhost step: the front-end config ${front_conf} was not found."

            # Phase A — the certificate-free :80 blocks with the acme-challenge location.
            local entry domain upstream internal_port
            local need_reload=0
            for entry in "$DEMO_DOMAIN:dev_aoa_demo:8100" "$MAXITOR_DOMAIN:dev_aoa_maxitor:8101"; do
                domain="${entry%%:*}"
                upstream="$(printf '%s' "$entry" | cut -d: -f2)"
                internal_port="${entry##*:}"
                if grep -q "proxy_pass http://${upstream}:${internal_port};" "$front_conf"; then
                    say "vhost step: ${domain} fully configured"
                    continue
                fi
                if grep -q "server_name ${domain};" "$front_conf"; then
                    say "vhost step: ${domain} already has its :80 block"
                else
                    cat >> "$front_conf" <<EOF

# ── ${domain} — demonstrator stand (issue #202) ───────────────────────────
server {
    listen 80;
    server_name ${domain};
    location /.well-known/acme-challenge/ { root /usr/share/nginx/html; }
    location / { return 301 https://${domain}\$request_uri; }
}
EOF
                fi
                need_reload=1
            done
            [[ $need_reload -eq 1 ]] && reload_nginx

            # Phase B — the certificates (the :80 blocks must be live for the webroot challenge).
            if certbot certificates 2>/dev/null | grep -q "$cert_name"; then
                say "certificate step: ${cert_name} already issued — renewed by the host's certbot timer."
            else
                certbot certonly --webroot -w "$webroot" -d "$DEMO_DOMAIN" -d "$MAXITOR_DOMAIN" \
                    --non-interactive --agree-tos --register-unsafely-without-email \
                    || fail "certificate step: certbot could not issue the certificates."
            fi
            if [[ ! -f "${ssl_dir}/${cert_name}.fullchain.pem" ]]; then
                cp "/etc/letsencrypt/live/${cert_name}/fullchain.pem" "${ssl_dir}/${cert_name}.fullchain.pem"
                cp "/etc/letsencrypt/live/${cert_name}/privkey.pem" "${ssl_dir}/${cert_name}.privkey.pem"
                mkdir -p /etc/letsencrypt/renewal-hooks/deploy
                cat > /etc/letsencrypt/renewal-hooks/deploy/aoa-dev-stand.sh <<'HOOK'
#!/bin/sh
# Copy the renewed dev-stand certificate into the front end's ssl mount and reload nginx-proxy.
set -e
if [ "$RENEWED_LINEAGE" = "/etc/letsencrypt/live/dev.demo.aoa.run" ]; then
    cp "/etc/letsencrypt/live/dev.demo.aoa.run/fullchain.pem" "/root/up2u_back/ssl/dev.demo.aoa.run.fullchain.pem"
    cp "/etc/letsencrypt/live/dev.demo.aoa.run/privkey.pem" "/root/up2u_back/ssl/dev.demo.aoa.run.privkey.pem"
    docker exec nginx-proxy nginx -s reload
fi
HOOK
                chmod +x /etc/letsencrypt/renewal-hooks/deploy/aoa-dev-stand.sh
            fi

            # Phase C — the :443 blocks, now that the certificate files exist.
            need_reload=0
            for entry in "$DEMO_DOMAIN:dev_aoa_demo:8100" "$MAXITOR_DOMAIN:dev_aoa_maxitor:8101"; do
                domain="${entry%%:*}"
                upstream="$(printf '%s' "$entry" | cut -d: -f2)"
                internal_port="${entry##*:}"
                if grep -q "proxy_pass http://${upstream}:${internal_port};" "$front_conf"; then
                    continue
                fi
                cat >> "$front_conf" <<EOF

server {
    listen 443 ssl;
    server_name ${domain};
    ssl_certificate     /etc/nginx/ssl/${cert_name}.fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/${cert_name}.privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://${upstream}:${internal_port};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
                need_reload=1
            done
            [[ $need_reload -eq 1 ]] && reload_nginx
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
        curl -fsS --retry 3 --retry-delay 2 --retry-all-errors "https://${DEMO_DOMAIN}/health" >/dev/null \
            || rollback "https verification failed for ${DEMO_DOMAIN}"
        curl -fsS --retry 3 --retry-delay 2 --retry-all-errors "https://${MAXITOR_DOMAIN}/api/health" >/dev/null \
            || rollback "https verification failed for ${MAXITOR_DOMAIN}"
    fi

    say "stand verified: ${DEMO_DOMAIN} + ${MAXITOR_DOMAIN}"
}

main "$@"
