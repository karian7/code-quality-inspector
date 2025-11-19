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

# 실제 설치 URL이 제공되는 경우 아래 주석을 해제하고 URL을 수정하세요
# curl -fsSL https://claude.ai/install.sh | bash
# 또는
# pip install claude-cli

# 개발 환경을 위한 더미 Claude CLI 스크립트 생성
if [ ! -f /usr/local/bin/claude ]; then
    echo "Creating mock Claude CLI for development..."
    cat > /usr/local/bin/claude << 'EOF'
#!/bin/bash
# Mock Claude CLI for development/testing

# 인자 파싱
case "$1" in
  analyze)
    # analyze 명령어 - 코드 분석
    echo '{"score": 85, "summary": "Mock Claude inspection result", "issues": [], "strengths": ["Well-structured code", "Good error handling"], "recommendations": ["Add more tests", "Improve documentation"]}'
    exit 0
    ;;
  --version|-v)
    # 버전 출력
    echo "Claude CLI Mock v1.0.0"
    exit 0
    ;;
  --help|-h)
    # 도움말
    echo "Mock Claude CLI - Development Version"
    echo "Usage: claude [analyze|--version|--help] [options]"
    exit 0
    ;;
  *)
    # 기본값 - 분석 결과 출력
    echo '{"score": 85, "summary": "Mock Claude inspection result", "issues": [], "strengths": ["Well-structured code"], "recommendations": ["Add more tests"]}'
    exit 0
    ;;
esac
EOF
    chmod +x /usr/local/bin/claude
    echo "Mock Claude CLI created at /usr/local/bin/claude"
fi

# Claude CLI 설치 확인
if command -v claude &> /dev/null; then
    echo "✓ Claude CLI installed successfully!"
    echo "  Version: $(claude --version 2>&1 || echo 'mock')"
else
    echo "✗ Warning: Claude CLI not found in PATH"
fi

# Codex CLI 설치
echo ""
echo "Installing Codex CLI..."
echo "----------------------------------------"

# 실제 설치 URL이 제공되는 경우 아래 주석을 해제하고 URL을 수정하세요
# curl -fsSL https://openai.com/codex/install.sh | bash
# 또는
# pip install openai-codex-cli

# 개발 환경을 위한 더미 Codex CLI 스크립트 생성
if [ ! -f /usr/local/bin/codex ]; then
    echo "Creating mock Codex CLI for development..."
    cat > /usr/local/bin/codex << 'EOF'
#!/bin/bash
# Mock Codex CLI for development/testing

# 인자 파싱
case "$1" in
  inspect)
    # inspect 명령어 - 코드 검사
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
    echo "Usage: codex [inspect|--version|--help] [options]"
    exit 0
    ;;
  *)
    # 기본값 - 검사 결과 출력
    echo '{"score": 88, "summary": "Mock Codex inspection result", "issues": [{"severity": "low", "category": "style", "file": "test.py", "line": 10, "description": "Line too long", "recommendation": "Break into multiple lines"}], "strengths": ["Good documentation", "Clear naming"], "recommendations": ["Consider adding type hints"]}'
    exit 0
    ;;
esac
EOF
    chmod +x /usr/local/bin/codex
    echo "Mock Codex CLI created at /usr/local/bin/codex"
fi

# Codex CLI 설치 확인
if command -v codex &> /dev/null; then
    echo "✓ Codex CLI installed successfully!"
    echo "  Version: $(codex --version 2>&1 || echo 'mock')"
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
echo "Note: Mock CLIs are installed for development."
echo "Replace with actual CLIs in production."
echo "=========================================="
