# GitHub Organization Scanner

Dockerized tool to scan GitHub organizations for repository health metrics. Optimized for large organizations with comprehensive reporting and configurable thresholds.

## Features

- **Orphaned Branch Detection**: Identifies branches without open PRs (includes merged/closed PR branches)
- **Old PR Analysis**: Configurable threshold for identifying stale pull requests
- **Performance Optimized**: Efficient API usage for large organizations (100+ repos)
- **Progress Tracking**: Real-time progress indicators during scanning
- **Comprehensive Reporting**: Both console summary and detailed JSON reports
- **Docker Isolation**: Secure, containerized execution

## Setup

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your settings:
   ```bash
   GITHUB_ORG=your-org-name
   GITHUB_TOKEN=ghp_your_token_here
   OLD_PR_THRESHOLD_DAYS=30
   ```

3. Run the scanner:
   ```bash
   make scan        # Build and run
   make fresh       # Force rebuild and run
   make build       # Build only
   make clean       # Clean up
   ```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_ORG` | Yes | - | GitHub organization name |
| `GITHUB_TOKEN` | Recommended | - | GitHub personal access token |
| `OLD_PR_THRESHOLD_DAYS` | No | 30 | Days to consider PRs as "old" |

### GitHub Token

- **Without token**: 60 requests/hour (rate limited)
- **With token**: 5000 requests/hour
- **Permissions needed**: `repo` (for private repos) or `public_repo` (for public repos only)

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make scan` | Build and run scanner |
| `make build` | Build Docker image |
| `make rebuild` | Force rebuild (no cache) |
| `make run` | Run existing image |
| `make fresh` | Rebuild and run |
| `make clean` | Remove containers and reports |
| `make logs` | View container logs |

## Repository Analysis

### What Gets Flagged as "Issues"

1. **More than 3 open PRs**
2. **PRs older than threshold** (configurable via `OLD_PR_THRESHOLD_DAYS`)
3. **Any orphaned branches** (branches without open PRs, excluding default/protected)

### Branch Classification

- **Total Branches**: All branches in the repository
- **Orphaned Branches**: Branches without open PRs (excludes default and protected branches)
- **Excluded from Orphaned Count**:
  - Default branch (main, master, etc.)
  - Protected branches
  - Branches with open PRs

## Output

### Console Output

- **Progress tracking**: Real-time scanning progress
- **Problem repos only**: Shows only repositories with issues
- **Clean summary**: Total repos, active repos, repos with issues, total open PRs
- **Issue details**: Branch counts, orphaned branches, old PR counts

### JSON Reports

- **Location**: `./reports/scan_{org}_{timestamp}.json`
- **Complete data**: All repositories with full metrics
- **Stale branches**: Complete list of orphaned branches (no limits)
- **Structured format**: Easy to parse and analyze

### Example Console Output

```
============================================================
GitHub Org: your-org
Scan Time: 2025-08-06 12:00:00
============================================================

Total repos: 96
Active repos (last year): 72

⚠️  problematic-repo
   Branches: 45 (23 orphaned)
   Old PRs (>30d): 2

============================================================
SUMMARY:
• Total repos: 96
• Active repos (last year): 72
• Repos with issues: 15
• Total open PRs: 42
• Repos needing attention listed above
============================================================
```

## Security

- **Docker isolation**: Runs in isolated container environment
- **Non-root execution**: Container runs as non-root user
- **No system access**: No direct access to host system
- **Environment variables**: Secure credential management
- **Local reports**: Reports saved to mounted volume only
- **No data persistence**: No data stored in container

## Performance

- **Optimized API calls**: Reduced API requests for better performance
- **Pagination handling**: Automatic handling of large datasets
- **Progress indicators**: Real-time feedback for long-running scans
- **Error handling**: Graceful handling of API failures
- **Rate limit aware**: Respects GitHub API rate limits

## Troubleshooting

### Permission Errors

- Ensure Docker has permission to create/write to `./reports/` directory
- Check that your user ID/group ID are properly set in docker-compose

### API Rate Limits

- Use a GitHub token for higher rate limits (5000/hour vs 60/hour)
- For very large organizations, consider running during off-peak hours

### Missing Repositories

- Ensure your GitHub token has access to all repositories in the organization
- Private repositories require `repo` scope, public repositories need `public_repo`
