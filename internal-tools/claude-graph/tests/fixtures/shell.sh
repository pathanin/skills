#!/bin/bash
# Shell names its lifecycle functions after bare verbs. Those are declarations,
# not fragments of a longer hyphenated name.
set -e

FTL_EXIT_CODE=0
readonly CONFIG_PATH=/etc/pihole

start() {
    echo "  [i] starting"
    ensure_basic_configuration
}

stop() {
    local code=$1
    echo "  [i] stopping"
    exit "$code"
}

ensure_basic_configuration() {
    : "${CONFIG_PATH:?}"
}

function validate_env {
    test -d "$CONFIG_PATH"
}

trap stop TERM INT QUIT HUP ERR
start
