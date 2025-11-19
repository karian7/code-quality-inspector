#!/bin/bash
set -e

echo "=========================================="
echo "AI CLI Installation Script"
echo "Installing Claude CLI and Codex CLI"
echo "=========================================="

# Claude CLI 설치
echo ""
echo "Installing Claude CLI..."
echo "----------------------------------------"

# Claude 디렉토리 생성
mkdir -p ~/.claude

# 온보딩 스킵 설정
cat > ~/.claude/.claude.json << 'EOF'
{
  "hasCompletedOnboarding": true
}
EOF

# API 키 헬퍼 설정 (환경변수 사용)
cat > ~/.claude/anthropic_key_helper.sh << 'EOF'
#!/bin/bash
echo ${ANTHROPIC_API_KEY}
EOF
chmod +x ~/.claude/anthropic_key_helper.sh

# settings.json 생성
cat > ~/.claude/settings.json << 'EOF'
{
  "apiKeyHelper": {
    "anthropic": "~/.claude/anthropic_key_helper.sh"
  }
}
EOF

# Claude Code 공식 설치
curl -fsSL https://claude.ai/install.sh | bash

# Claude CLI 설치 확인
if command -v claude &> /dev/null; then
    echo "✓ Claude CLI installed successfully!"
    echo "  Version: $(claude --version 2>&1 || echo 'unknown')"
else
    echo "✗ Warning: Claude CLI not found in PATH"
fi

# Codex CLI 설치
echo ""
echo "Installing Codex CLI..."
echo "----------------------------------------"

# npm을 통한 Codex CLI 설치
npm i -g @openai/codex

# Codex CLI 설치 확인
if command -v codex &> /dev/null; then
    echo "✓ Codex CLI installed successfully!"
    echo "  Version: $(codex --version 2>&1 || echo 'unknown')"
else
    echo "✗ Warning: Codex CLI not found in PATH"
fi

echo ""
echo "=========================================="
echo "Installation Summary"
echo "=========================================="
echo "Claude CLI: $(command -v claude &> /dev/null && echo '✓ Available' || echo '✗ Not found')"
echo "Codex CLI:  $(command -v codex &> /dev/null && echo '✓ Available' || echo '✗ Not found')"
echo ""
echo "AI CLIs are ready for use."
echo "=========================================="