# Code Quality Inspector

Automated code quality inspection service powered by Claude AI. This service automatically analyzes GitHub repositories and provides detailed quality reports based on predefined inspection rules.

## Features

- 🔍 **Automated Code Analysis**: Analyzes code quality using Claude AI
- 🚀 **Asynchronous Processing**: Uses Celery for background task processing
- 📊 **Detailed Reports**: Provides comprehensive quality scores and recommendations
- 🔒 **Secure**: API key authentication and secure code handling
- 📦 **Docker-Ready**: Complete Docker Compose setup for easy deployment
- 🎯 **Flexible Rules**: Customizable inspection rules for quality, security, and performance

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  FastAPI    │────▶│   Redis     │
└─────────────┘     │   Server    │     │   Broker    │
                    └─────────────┘     └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │   Celery    │
                                        │   Workers   │
                                        └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │  Claude CLI │
                                        │  Inspector  │
                                        └─────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Anthropic API Key (for Claude AI)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd code-quality-inspector
```

2. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
```

3. Start the services:
```bash
docker-compose up -d
```

4. Verify the services are running:
```bash
curl http://localhost:8000/health
```

## Usage

### API Endpoints

#### 1. Create Inspection Task

```bash
POST /api/inspect
```

**Request Body:**
```json
{
  "github_url": "https://github.com/user/repo",
  "branch": "main",
  "callback_url": "https://your-server.com/webhook",
  "rules_files": ["quality_rules.md", "security_rules.md"],
  "metadata": {
    "project_id": "123",
    "user_id": "456"
  }
}
```

**Response:**
```json
{
  "task_id": "abc-123-def-456",
  "status": "queued",
  "message": "Inspection task has been queued successfully",
  "created_at": "2025-01-18T10:00:00Z"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/inspect \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "github_url": "https://github.com/user/repo",
    "branch": "main",
    "callback_url": "https://your-server.com/webhook",
    "rules_files": ["quality_rules.md"]
  }'
```

#### 2. Check Task Status

```bash
GET /api/status/{task_id}
```

**Response:**
```json
{
  "task_id": "abc-123-def-456",
  "status": "success",
  "result": {
    "score": 85,
    "summary": "Code quality is good with minor issues",
    "issues": [...],
    "strengths": [...],
    "recommendations": [...]
  },
  "created_at": "2025-01-18T10:00:00Z"
}
```

#### 3. Callback Payload

When inspection completes, the service sends results to your callback URL:

```json
{
  "task_id": "abc-123-def-456",
  "status": "success",
  "github_url": "https://github.com/user/repo",
  "branch": "main",
  "result": {
    "score": 85,
    "summary": "Code quality analysis complete",
    "issues": [
      {
        "severity": "medium",
        "category": "code_quality",
        "file": "src/main.py",
        "line": 42,
        "description": "Function too long",
        "recommendation": "Break into smaller functions"
      }
    ],
    "strengths": [
      "Well-structured code",
      "Good test coverage"
    ],
    "recommendations": [
      "Add more documentation",
      "Reduce code duplication"
    ],
    "repository_info": {
      "commit_sha": "abc123...",
      "commit_message": "Latest changes",
      "author": "John Doe",
      "committed_date": "2025-01-18T09:00:00Z"
    }
  },
  "metadata": {
    "project_id": "123"
  },
  "completed_at": "2025-01-18T10:05:00Z"
}
```

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for full list):

- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `API_KEYS`: JSON array of allowed API keys for authentication
- `CELERY_WORKER_CONCURRENCY`: Number of concurrent workers (default: 5)
- `CLAUDE_MODEL`: Claude model to use (default: claude-3-opus-20240229)

### Inspection Rules

The service includes three types of inspection rules:

1. **Quality Rules** (`rules/quality_rules.md`): Code structure, naming, complexity
2. **Security Rules** (`rules/security_rules.md`): OWASP Top 10, secure coding practices
3. **Performance Rules** (`rules/performance_rules.md`): Algorithmic efficiency, optimization

You can customize these rules or create new ones.

## Development

### Local Development Setup

1. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run tests:
```bash
pytest
```

3. Run with auto-reload:
```bash
uvicorn app.main:app --reload
```

4. Start Celery worker:
```bash
celery -A app.core.celery_app worker --loglevel=info
```

### Project Structure

```
code-quality-inspector/
├── app/
│   ├── api/              # API routes and schemas
│   ├── core/             # Core functionality (Celery, logging, security)
│   ├── services/         # Business logic (Git, Inspector, Rules)
│   ├── tasks/            # Celery tasks
│   ├── templates/        # HTML templates
│   └── main.py           # FastAPI application
├── rules/                # Inspection rule definitions
├── scripts/              # Helper scripts
├── tests/                # Test suite
├── docker-compose.yml    # Docker Compose configuration
└── Dockerfile.*          # Docker configurations
```

## Monitoring

### Flower Dashboard

Access Celery task monitoring at `http://localhost:5555`

### Logs

View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f worker
docker-compose logs -f web
```

## API Authentication

The service uses API key authentication via the `X-API-Key` header.

Configure allowed API keys in `.env`:
```
API_KEYS=["your-api-key-1","your-api-key-2"]
```

## Troubleshooting

### Claude CLI Not Found

If you see "Claude CLI not found" errors:

1. Check the installation script: `scripts/install_claude.sh`
2. Update with actual Claude CLI installation method
3. Rebuild Docker images: `docker-compose build`

### Worker Not Processing Tasks

1. Check Redis connection: `docker-compose logs redis`
2. Verify worker logs: `docker-compose logs worker`
3. Check Flower dashboard: `http://localhost:5555`

### Callback Failures

1. Ensure callback URL is accessible from Docker network
2. Check callback service logs
3. Verify callback endpoint accepts POST requests

## Performance Tuning

- Adjust `CELERY_WORKER_CONCURRENCY` based on CPU cores
- Scale workers: `docker-compose up -d --scale worker=5`
- Configure Redis memory limits
- Adjust Claude API timeout settings

## Security Considerations

- Never commit `.env` file with real credentials
- Use strong API keys (32+ characters)
- Restrict CORS origins in production
- Enable HTTPS for production deployments
- Regularly update dependencies
- Monitor and rotate API keys

## License

[Your License Here]

## Contributing

[Contributing Guidelines]

## Support

For issues and questions:
- GitHub Issues: [Repository Issues URL]
- Documentation: See `code-quality-inspector-prd.md`

## Changelog

### Version 1.0.0 (2025-01-18)
- Initial release
- FastAPI web server
- Celery worker integration
- Claude AI code inspection
- Docker Compose setup
- Quality, Security, and Performance rules
