# GitHub Organization Scanner

Dockerized tool to scan GitHub organizations for repository health metrics.

## Setup

1. Copy `.env.example` to `.env` and add your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your GITHUB_ORG and GITHUB_TOKEN
   ```

2. Run the scanner:
   ```bash
   make scan
   # or
   docker-compose run --rm github-scanner
   ```

3. Check reports in `./reports/` directory

## Security

- Runs in isolated Docker container
- Non-root user inside container
- No direct OS access
- Credentials via environment variables
- Reports saved locally in mounted volume

## Output

- Console: Shows only repos with issues (old PRs, orphaned branches)
- JSON: Full report saved with timestamp
