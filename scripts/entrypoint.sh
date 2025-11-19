#!/bin/bash
set -e

# Codex auth.json 파일 생성 (환경변수에서 API 키 주입)
if [ -n "$OPENAI_API_KEY" ]; then
    echo "Configuring Codex authentication..."
    mkdir -p /root/.codex
    cat > /root/.codex/auth.json << EOF
{
  "OPENAI_API_KEY": "$OPENAI_API_KEY"
}
EOF
    echo "✓ Codex auth.json configured with OPENAI_API_KEY"
else
    echo "⚠ Warning: OPENAI_API_KEY not set, Codex authentication may fail"
fi

# 원래 CMD 실행
exec "$@"
