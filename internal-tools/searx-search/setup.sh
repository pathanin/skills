#!/bin/sh
# Install a local SearXNG for search.py. Safe to re-run: keeps an existing settings.yml.
# Needs: uv, curl, tar. Override the location with SEARXNG_ROOT.
set -eu

ROOT="${SEARXNG_ROOT:-$HOME/.local/share/searxng}"
mkdir -p "$ROOT"
cd "$ROOT"

command -v uv >/dev/null || { echo "uv not found (brew install uv)" >&2; exit 1; }

if [ ! -f src/searx/webapp.py ]; then
  echo "Downloading SearXNG source..."
  rm -rf src.tmp && mkdir src.tmp
  curl -fsSL https://github.com/searxng/searxng/archive/refs/heads/master.tar.gz \
    | tar -xz -C src.tmp --strip-components=1
  rm -rf src && mv src.tmp src
fi

if [ ! -x venv/bin/python ]; then
  uv venv --python 3.12 venv
fi
echo "Installing dependencies..."
VIRTUAL_ENV="$ROOT/venv" uv pip install -q -r src/requirements.txt

if [ ! -f settings.yml ]; then
  secret=$(openssl rand -hex 32)
  umask 077
  cat > settings.yml <<EOF
# Local SearXNG for the searx-search skill. Overrides defaults in src/searx/settings.yml.
use_default_settings: true
general:
  instance_name: "local"
search:
  safe_search: 0
  formats: [html, json]
server:
  bind_address: "127.0.0.1"  # port comes from SEARXNG_PORT (search.py uses 18888)
  secret_key: "$secret"
  limiter: false
  public_instance: false
  image_proxy: false
outgoing:
  request_timeout: 4.0
  max_request_timeout: 8.0
EOF
fi

echo "SearXNG ready at $ROOT"
