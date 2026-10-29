#!/usr/bin/env bash
# scripts/deploy_demonstrator_stand.sh — one-command deployment for the demonstrator stand.
#
# The stand is accepted by opening its URLs and by running one command — this
# script is that command. In order: DNS and TLS-terminator gates, build the
# images (demo, Maxitor, repo-graph-port), start the containers, poll their health,
# verify every domain, and roll back to the previously running images on any failure. On nginx, every run
# also makes sure Maxitor's vhost passes room WebSockets (spec 028), including a
# vhost an earlier run wrote.
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
# The host wiring (front-end network + aliases) lives in the override named
# `docker-compose.host.yml`, derived from the base file's name. It is appended
# when present — local runs use the base compose alone, and a host run without
# it is refused below rather than silently deploying containers the front end
# cannot resolve.
COMPOSE_HOST_FILE="${COMPOSE_FILE%.yml}.host.yml"
COMPOSE_LOCAL_FILE="${COMPOSE_FILE%.yml}.local.yml"

LOCAL_MODE=0
if [[ "${1:-}" == "--local" ]]; then
    LOCAL_MODE=1
fi

# A host run joins the front end's network through the host overlay; a local run
# never can (that network exists only on the host) and uses the local overlay
# instead, which gives the containers the alias the demo is reached by.
COMPOSE_ARGS=(-f "$COMPOSE_FILE")
if [[ $LOCAL_MODE -eq 0 && -f "$COMPOSE_HOST_FILE" ]]; then
    COMPOSE_ARGS+=(-f "$COMPOSE_HOST_FILE")
fi
if [[ $LOCAL_MODE -eq 1 ]]; then
    [[ -f "$COMPOSE_LOCAL_FILE" ]] || { printf 'FAIL: %s is missing — the local run cannot reach the demo without it\n' "$COMPOSE_LOCAL_FILE"; exit 1; }
    COMPOSE_ARGS+=(-f "$COMPOSE_LOCAL_FILE")
fi

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
REPO_GRAPH_PORT_DOMAIN="${REPO_GRAPH_PORT_DOMAIN:-repo-graph-port.aoa.run}"
REPO_GRAPH_PORT_PORT="${REPO_GRAPH_PORT_PORT:-8103}"
SERVICES=(demo maxitor repo-graph-port)

say() { printf '%s\n' "$*"; }
fail() { say "FAIL: $*"; exit 1; }
rollback() {
    say "ROLLBACK: $*"
    say "restoring the previous images and containers..."
    for service in "${SERVICES[@]}"; do
        if docker image inspect "stand-${service}:backup" >/dev/null 2>&1; then
            docker image tag "stand-${service}:backup" "stand-${service}:latest"
        fi
    done
    docker compose "${COMPOSE_ARGS[@]}" up -d >/dev/null 2>&1 || true
    exit 1
}

gate_dns() {
    [[ $LOCAL_MODE -eq 1 ]] && return 0
    for domain in "$DEMO_DOMAIN" "$MAXITOR_DOMAIN" "$REPO_GRAPH_PORT_DOMAIN"; do
        if ! python3 -c "import socket, sys; socket.getaddrinfo(sys.argv[1], None)" "$domain" >/dev/null 2>&1; then
            fail "DNS gate: '$domain' does not resolve — create the A record before deploying."
        fi
    done
    say "DNS gate: every domain resolves"
}

detect_terminator() {
    [[ $LOCAL_MODE -eq 1 ]] && { echo "local"; return 0; }
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx nginx-proxy; then echo "nginx"; return 0; fi
    if command -v nginx >/dev/null 2>&1; then echo "nginx"; return 0; fi
    if command -v caddy >/dev/null 2>&1; then echo "caddy"; return 0; fi
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qi traefik; then echo "traefik"; return 0; fi
    return 1
}

test_nginx() {
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx nginx-proxy; then
        docker exec nginx-proxy nginx -t
    else
        nginx -t
    fi
}

reload_nginx() {
    test_nginx || fail "vhost step: nginx -t rejected the new virtual hosts."
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx nginx-proxy; then
        docker exec nginx-proxy nginx -s reload || fail "vhost step: nginx reload failed."
    else
        systemctl reload nginx || fail "vhost step: nginx reload failed."
    fi
}

# Maxitor's rooms run over a WebSocket (spec 028): its :443 block needs a
# `location /api/v1/rooms/` that passes the upgrade through, keeps the page's
# Host (a foreign Host is refused with 4403) and keeps a quiet connection open.
# Inserted before the block's `location /`, into a block written by this script
# or by an earlier run alike; a block that already has it is left as it is.
# Succeeds only when it changed the file, so the caller knows to reload.
add_rooms_location() {
    local front_conf="$1" domain="$2" upstream="$3" internal_port="$4"
    local edited original status=0
    edited="$(mktemp)"
    original="$(mktemp)"
    awk -v domain="$domain" -v upstream="$upstream" -v port="$internal_port" '
        # Each top-level server block is buffered and printed when it closes;
        # everything outside server blocks is printed as it comes.
        function rooms_location() {
            print "    location /api/v1/rooms/ {"
            print "        proxy_pass http://" upstream ":" port ";"
            print "        proxy_http_version 1.1;"
            print "        proxy_set_header Upgrade $http_upgrade;"
            print "        proxy_set_header Connection \"upgrade\";"
            print "        proxy_set_header Host $host;"
            print "        proxy_set_header X-Real-IP $remote_addr;"
            print "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;"
            print "        proxy_set_header X-Forwarded-Proto $scheme;"
            print "        proxy_read_timeout 1h;"
            print "    }"
            print ""
        }
        function flush(   i, ssl, named, present, done) {
            for (i = 1; i <= n; i++) {
                if (index(buf[i], "listen 443")) ssl = 1
                if (index(buf[i], "server_name " domain ";")) named = 1
                if (index(buf[i], "location /api/v1/rooms/")) present = 1
            }
            if (ssl && named) state = present ? 3 : 0
            for (i = 1; i <= n; i++) {
                if (ssl && named && !present && !done && (buf[i] ~ /^[[:space:]]*location \/ *\{/ || i == n)) {
                    rooms_location()
                    done = 1
                }
                print buf[i]
            }
            n = 0
        }
        BEGIN { state = 4 }
        depth == 0 && $0 !~ /^[[:space:]]*server[[:space:]]*\{/ { print; next }
        {
            buf[++n] = $0
            depth += gsub(/\{/, "{") - gsub(/\}/, "}")
            if (depth == 0) flush()
        }
        END { if (n) flush(); exit state }
    ' "$front_conf" > "$edited" || status=$?
    case "$status" in
        0)
            cp "$front_conf" "$original"
            # Written in place, not moved: nginx-proxy reads this file through a
            # single-file bind mount, which a new inode would leave behind.
            cat "$edited" > "$front_conf"
            if ! test_nginx; then
                cat "$original" > "$front_conf"
                rm -f "$edited" "$original"
                fail "vhost step: nginx -t rejected the rooms location for ${domain}; the previous config is restored."
            fi
            say "vhost step: ${domain} passes WebSockets to /api/v1/rooms/"
            rm -f "$edited" "$original"
            return 0
            ;;
        3)
            say "vhost step: ${domain} already passes WebSockets to /api/v1/rooms/"
            rm -f "$edited" "$original"
            return 1
            ;;
        *)
            rm -f "$edited" "$original"
            fail "vhost step: no :443 block for ${domain} in ${front_conf} to add the rooms location to."
            ;;
    esac
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
            for entry in "$DEMO_DOMAIN:dev_aoa_demo:8100" "$MAXITOR_DOMAIN:dev_aoa_maxitor:8101" "$REPO_GRAPH_PORT_DOMAIN:dev_aoa_repo_graph_port:8102"; do
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
            # The port has a certificate of its own: its domain is not a dev.* name of the stand.
            if certbot certificates 2>/dev/null | grep -q "$REPO_GRAPH_PORT_DOMAIN"; then
                say "certificate step: ${REPO_GRAPH_PORT_DOMAIN} already issued — renewed by the host's certbot timer."
            else
                certbot certonly --webroot -w "$webroot" -d "$REPO_GRAPH_PORT_DOMAIN" \
                    --non-interactive --agree-tos --register-unsafely-without-email \
                    || fail "certificate step: certbot could not issue the certificate of ${REPO_GRAPH_PORT_DOMAIN}."
            fi
            if [[ ! -f "${ssl_dir}/${REPO_GRAPH_PORT_DOMAIN}.fullchain.pem" ]]; then
                cp "/etc/letsencrypt/live/${REPO_GRAPH_PORT_DOMAIN}/fullchain.pem" "${ssl_dir}/${REPO_GRAPH_PORT_DOMAIN}.fullchain.pem"
                cp "/etc/letsencrypt/live/${REPO_GRAPH_PORT_DOMAIN}/privkey.pem" "${ssl_dir}/${REPO_GRAPH_PORT_DOMAIN}.privkey.pem"
                mkdir -p /etc/letsencrypt/renewal-hooks/deploy
                cat > /etc/letsencrypt/renewal-hooks/deploy/aoa-repo-graph-port.sh <<HOOK
#!/bin/sh
# Copy the renewed repo-graph-port certificate into the front end's ssl mount and reload nginx-proxy.
set -e
if [ "\$RENEWED_LINEAGE" = "/etc/letsencrypt/live/${REPO_GRAPH_PORT_DOMAIN}" ]; then
    cp "/etc/letsencrypt/live/${REPO_GRAPH_PORT_DOMAIN}/fullchain.pem" "${ssl_dir}/${REPO_GRAPH_PORT_DOMAIN}.fullchain.pem"
    cp "/etc/letsencrypt/live/${REPO_GRAPH_PORT_DOMAIN}/privkey.pem" "${ssl_dir}/${REPO_GRAPH_PORT_DOMAIN}.privkey.pem"
    docker exec nginx-proxy nginx -s reload
fi
HOOK
                chmod +x /etc/letsencrypt/renewal-hooks/deploy/aoa-repo-graph-port.sh
            fi

            # Phase C — the :443 blocks, now that the certificate files exist.
            need_reload=0
            for entry in "$DEMO_DOMAIN:dev_aoa_demo:8100" "$MAXITOR_DOMAIN:dev_aoa_maxitor:8101" "$REPO_GRAPH_PORT_DOMAIN:dev_aoa_repo_graph_port:8102"; do
                domain="${entry%%:*}"
                upstream="$(printf '%s' "$entry" | cut -d: -f2)"
                internal_port="${entry##*:}"
                if grep -q "proxy_pass http://${upstream}:${internal_port};" "$front_conf"; then
                    continue
                fi
                # The port's domain has its own certificate; GitHub's webhook bodies can be large.
                local block_cert="$cert_name" body_limit=""
                if [[ "$domain" == "$REPO_GRAPH_PORT_DOMAIN" ]]; then
                    block_cert="$REPO_GRAPH_PORT_DOMAIN"
                    body_limit="    client_max_body_size 25m;"
                fi
                cat >> "$front_conf" <<EOF

server {
    listen 443 ssl;
    server_name ${domain};
    ssl_certificate     /etc/nginx/ssl/${block_cert}.fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/${block_cert}.privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
${body_limit}

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
            add_rooms_location "$front_conf" "$MAXITOR_DOMAIN" dev_aoa_maxitor 8101 && need_reload=1
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
${REPO_GRAPH_PORT_DOMAIN} {
    reverse_proxy 127.0.0.1:${REPO_GRAPH_PORT_PORT}
}
EOF
            systemctl reload caddy || fail "vhost step: caddy reload failed."
            ;;
        *)
            fail "terminator gate: detected '${terminator}' is not scripted — add the virtual hosts manually and name this gap."
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
    for service in "${SERVICES[@]}"; do
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

    if [[ $LOCAL_MODE -eq 0 && ! -f "$COMPOSE_HOST_FILE" ]]; then
        fail "overlay gate: '$COMPOSE_HOST_FILE' is missing — without it the containers never join the front end's network, and the virtual hosts point at a name nothing resolves."
    fi

    say "=== build ==="
    docker compose "${COMPOSE_ARGS[@]}" build

    say "=== snapshot for rollback ==="
    backup_images

    say "=== up ==="
    docker compose "${COMPOSE_ARGS[@]}" up -d

    say "=== health ==="
    wait_healthy demo || rollback "the demo container did not become healthy"
    wait_healthy maxitor || rollback "the Maxitor container did not become healthy"
    wait_healthy repo-graph-port || rollback "the repo-graph-port container did not become healthy"
    # The containers may have been recreated with new network addresses; nginx
    # resolves upstream names once per reload, so re-resolve them now.
    if [[ $LOCAL_MODE -eq 0 ]]; then
        reload_nginx
    fi

    say "=== verify ==="
    if [[ $LOCAL_MODE -eq 1 ]]; then
        curl -fsS "http://127.0.0.1:${DEMO_PORT}/health" >/dev/null || rollback "local verification failed for the demo"
        curl -fsS "http://127.0.0.1:${MAXITOR_PORT}/api/health" >/dev/null || rollback "local verification failed for Maxitor"
        curl -fsS "http://127.0.0.1:${REPO_GRAPH_PORT_PORT}/health" >/dev/null || rollback "local verification failed for repo-graph-port"
    else
        install_vhosts "$terminator" || rollback "virtual-host installation failed"
        curl -fsS --retry 3 --retry-delay 2 --retry-all-errors "https://${DEMO_DOMAIN}/health" >/dev/null \
            || rollback "https verification failed for ${DEMO_DOMAIN}"
        curl -fsS --retry 3 --retry-delay 2 --retry-all-errors "https://${MAXITOR_DOMAIN}/api/health" >/dev/null \
            || rollback "https verification failed for ${MAXITOR_DOMAIN}"
        curl -fsS --retry 3 --retry-delay 2 --retry-all-errors "https://${REPO_GRAPH_PORT_DOMAIN}/health" >/dev/null \
            || rollback "https verification failed for ${REPO_GRAPH_PORT_DOMAIN}"
    fi

    say "stand verified: ${DEMO_DOMAIN} + ${MAXITOR_DOMAIN} + ${REPO_GRAPH_PORT_DOMAIN}"
}

main "$@"
