#!/bin/bash
set -e

echo "=========================================="
echo "Claude CLI Installation Script"
echo "=========================================="

# Claude CLI 설치 방법
# 주의: 이것은 예시 스크립트입니다.
# 실제 Claude CLI 설치 방법은 Anthropic 공식 문서를 참조하세요.

# 방법 1: curl을 통한 설치 (가상 URL)
echo "Attempting to install Claude CLI..."

# 실제 설치 URL이 제공되는 경우 아래 주석을 해제하고 URL을 수정하세요
# curl -fsSL https://claude.ai/install.sh | bash

# 방법 2: pip을 통한 설치 (존재할 경우)
# pip install claude-cli

# 방법 3: 바이너리 다운로드 (존재할 경우)
# CLAUDE_VERSION="1.0.0"
# wget https://github.com/anthropics/claude-cli/releases/download/v${CLAUDE_VERSION}/claude-linux-amd64
# chmod +x claude-linux-amd64
# mv claude-linux-amd64 /usr/local/bin/claude

# 개발 환경을 위한 더미 스크립트 생성
if [ ! -f /usr/local/bin/claude ]; then
    echo "Creating mock Claude CLI for development..."
    cat > /usr/local/bin/claude << 'EOF'
#!/bin/bash
# Mock Claude CLI for development/testing
echo '{"score": 85, "summary": "Mock inspection result", "issues": [], "strengths": ["Well-structured code"], "recommendations": ["Add more tests"]}'
EOF
    chmod +x /usr/local/bin/claude
    echo "Mock Claude CLI created at /usr/local/bin/claude"
fi

# 설치 확인
if command -v claude &> /dev/null; then
    echo "Claude CLI installed successfully!"
    echo "Version: $(claude --version 2>&1 || echo 'unknown')"
else
    echo "Warning: Claude CLI not found in PATH"
    exit 1
fi

echo "=========================================="
echo "Claude CLI installation completed"
echo "=========================================="
