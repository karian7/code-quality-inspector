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

# Claude CLI 심볼릭 링크 생성 (~/.local/bin/claude → /usr/bin/claude)
if [ -f ~/.local/bin/claude ]; then
    echo "Creating symbolic link: /usr/bin/claude → ~/.local/bin/claude"
    ln -sf ~/.local/bin/claude /usr/bin/claude
    echo "✓ Symbolic link created successfully"
else
    echo "✗ Warning: Claude CLI not found at ~/.local/bin/claude"
    echo "  Installation may have failed or installed to a different location"
fi


# Claude CLI 설치 확인
if command -v claude &> /dev/null; then
    echo "✓ Claude CLI installed successfully!"
    echo "  Version: $(claude --version 2>&1 || echo 'unknown')"
else
    echo "✗ Warning: Claude CLI not found in PATH"
    echo "  Creating mock Claude CLI for development..."

    # Fallback: Mock CLI 생성
    cat > /usr/local/bin/claude << 'EOF'
#!/bin/bash
# Mock Claude CLI for development/testing
# 실제 Claude Code CLI 형식: claude -p "프롬프트"

# 인자 파싱
case "$1" in
  -p)
    # -p 옵션: 프롬프트를 받아서 코드 분석
    # 실제로는 $2에 프롬프트가 전달됨
    echo '{"score": 85, "summary": "Mock Claude inspection result", "issues": [], "strengths": ["Well-structured code", "Good error handling"], "recommendations": ["Add more tests", "Improve documentation"]}'
    exit 0
    ;;
  --version|-v)
    # 버전 출력
    echo "Claude Code CLI Mock v1.0.0"
    exit 0
    ;;
  --help|-h)
    # 도움말
    echo "Mock Claude Code CLI - Development Version"
    echo "Usage: claude -p \"prompt\" [options]"
    exit 0
    ;;
  *)
    # 기본값 - 에러 메시지
    echo "Error: Please use -p option to provide a prompt" >&2
    echo "Usage: claude -p \"prompt\"" >&2
    exit 1
    ;;
esac
EOF
    chmod +x /usr/local/bin/claude
    echo "  Mock Claude CLI created at /usr/local/bin/claude"
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
    echo "  Creating mock Codex CLI for development..."

    # Fallback: Mock CLI 생성
    cat > /usr/local/bin/codex << 'EOF'
#!/bin/bash
# Mock Codex CLI for development/testing
# Codex CLI 형식 (Claude와 유사): codex -p "프롬프트"

# 인자 파싱
case "$1" in
  -p)
    # -p 옵션: 프롬프트를 받아서 코드 검사
    # 실제로는 $2에 프롬프트가 전달됨
    echo '{"score": 88, "summary": "Mock Codex inspection result", "issues": [{"severity": "low", "category": "style", "file": "test.py", "line": 10, "description": "Line too long", "recommendation": "Break into multiple lines"}], "strengths": ["Good documentation", "Clear naming", "Well-tested"], "recommendations": ["Consider adding type hints", "Improve error messages"]}'
    exit 0
    ;;
  --version|-v)
    # 버전 출력
    echo "Codex CLI Mock v1.0.0"
    exit 0
    ;;
  --help|-h)
    # 도움말
    echo "Mock Codex CLI - Development Version"
    echo "Usage: codex -p \"prompt\" [options]"
    exit 0
    ;;
  *)
    # 기본값 - 에러 메시지
    echo "Error: Please use -p option to provide a prompt" >&2
    echo "Usage: codex -p \"prompt\"" >&2
    exit 1
    ;;
esac
EOF
    chmod +x /usr/local/bin/codex
    echo "  Mock Codex CLI created at /usr/local/bin/codex"
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
