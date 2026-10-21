#!/bin/sh
# Keep stdout exclusively for MCP JSON-RPC. Never change global xcode-select.
set -eu
if [ -n "${XCODE_APP:-}" ]; then
    DEVELOPER_DIR="${XCODE_APP%/}/Contents/Developer"
    export DEVELOPER_DIR
elif [ -z "${DEVELOPER_DIR:-}" ]; then
    selected=$(/usr/bin/xcode-select -p 2>/dev/null || true)
    if [ -x "$selected/usr/bin/mcpbridge" ]; then
        DEVELOPER_DIR="$selected"
    else
        DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"
    fi
    export DEVELOPER_DIR
fi
if [ ! -x "$DEVELOPER_DIR/usr/bin/mcpbridge" ]; then
    echo "Xcode MCP bridge unavailable. Set XCODE_APP or DEVELOPER_DIR to a compatible Xcode installation." >&2
    exit 1
fi
exec /usr/bin/xcrun mcpbridge "$@"
