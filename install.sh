-#!/bin/bash

if ! command -v uv &> /dev/null; then
    echo "🚀 uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    export PATH="$HOME/.local/bin:$PATH"

    CURRENT_SHELL=$(basename "$SHELL")
    RC_FILE="$HOME/.${CURRENT_SHELL}rc"
    
    [ ! -f "$RC_FILE" ] && RC_FILE="$HOME/.profile"

    if ! grep -q ".local/bin" "$RC_FILE"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC_FILE"
        echo "✅ Added to $RC_FILE"
    fi
else
    echo "✅ uv already installed."
fi

echo "📦 Syncing project..."
uv sync
