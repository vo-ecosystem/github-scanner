# GitHub Organization Scanner

Dockerized tool to scan GitHub organizations for repository health metrics. Optimized for large organizations with comprehensive reporting and configurable thresholds.

## Features

- **Orphaned Branch Detection**: Identifies branches without open PRs (includes merged/closed PR branches)
- **Closed/Merged PR Branch Tracking**: Identifies branches that still exist after their PRs were closed or merged
- **Old PR Analysis**: Configurable threshold for identifying stale pull requests
- **Pretty-Print Table Format**: Human-friendly table output for stale PRs and orphaned branches
- **Discord Integration**: Automated report uploads to Discord via GitHub Actions
- **Performance Optimized**: Efficient API usage for large organizations (100+ repos)
- **Progress Tracking**: Real-time progress indicators during scanning
- **Comprehensive Reporting**: Both console summary and detailed JSON/Markdown reports
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

### Creating GitHub Token with Minimal Permissions

To create a GitHub Personal Access Token with minimal required permissions:

1. **Go to GitHub Settings**:
   - Navigate to [GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)](https://github.com/settings/tokens)
   - Or go to your GitHub profile → Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Generate New Token**:
   - Click "Generate new token" → "Generate new token (classic)"
   - Give it a descriptive name (e.g., "GitHub Scanner - [Organization Name]")
   - Set expiration date (recommended: 90 days for security)

3. **Select Minimal Required Scopes**:
   - **`repo`** - Full control of private repositories (required for accessing repository data)
   - **`read:org`** - Read organization membership and teams (required for organization scanning)

   **Note**: If you only need to scan public repositories, you can use `public_repo` instead of full `repo` scope.

4. **For Organization Access**:
   - If scanning private repositories in an organization, ensure your token has access
   - Organization owners may need to approve token access for private repos
   - Check organization settings under "Third-party application access policy"

5. **Security Best Practices**:
   - Store the token securely (never commit to version control)
   - Use environment variables or `.env` files (already in `.gitignore`)
   - Regularly rotate tokens (set shorter expiration periods)
   - Revoke unused tokens immediately

6. **Token Format**:
   ```
   ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

3. Run the scanner:
   ```bash
   make scan        # Build and run (JSON output)
   make pretty      # Build and run with pretty table output
   make fresh       # Force rebuild and run
   make build       # Build only
   make clean       # Clean up
   ```

## Single Repository Scan

By default, the scanner analyzes all repositories in an organization. You can scan a specific repository instead by setting the `GITHUB_REPO` environment variable.

### Usage Examples

```bash
# Scan entire organization (default JSON output)
make fresh

# Scan with pretty table output
make pretty

# Scan only a specific repository
GITHUB_REPO=my-repo-name make fresh

# Scan specific repository with pretty output
GITHUB_REPO=my-repo-name make pretty

# Or set it in your .env file
echo "GITHUB_REPO=my-repo-name" >> .env
make fresh
```

### When to Use Single Repository Scan

- **Testing**: Quickly test the scanner on a specific repository
- **Focused Analysis**: Deep dive into a particular repository's health
- **Performance**: Faster execution when you only need data for one repo
- **Development**: Debugging or developing new features

### Output Differences

- **Header**: Shows `GitHub Repo: org/repo-name` instead of `GitHub Org: org-name`
- **Report File**: Named `scan_org_repo_timestamp.json` instead of `scan_org_timestamp.json`
- **Summary**: Always shows 1 total repo and 1 active repo (if the repo has recent activity)

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_ORG` | Yes | - | GitHub organization name |
| `GITHUB_TOKEN` | Recommended | - | GitHub personal access token |
| `GITHUB_REPO` | No | - | Specific repository name (scans only this repo instead of entire org) |
| `OLD_PR_THRESHOLD_DAYS` | No | 30 | Days to consider PRs as "old" |

### GitHub Token

- **Without token**: 60 requests/hour (rate limited)
- **With token**: 5000 requests/hour
- **Permissions needed**: `repo` (for private repos) or `public_repo` (for public repos only)

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make scan` | Build and run scanner (JSON output) |
| `make pretty` | Build and run with pretty table output |
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

### Console Output (Default)

- **Progress tracking**: Real-time scanning progress
- **Problem repos only**: Shows only repositories with issues
- **Clean summary**: Total repos, active repos, repos with issues, total open PRs
- **Issue details**: Branch counts, orphaned branches, old PR counts

### Pretty Table Output (with `-p` or `--pretty` flag)

- **Human-friendly table**: Formatted table with stale PRs and orphaned branches
- **Closed/Merged PR branches**: Separate section showing branches that still exist after PR closure/merge
- **Detailed information**: Repository, type (Stale PR/Orphaned Branch), item name, user/author, age, and direct link
- **Easy to read**: Perfect for manual review and sharing with team members
- **Includes summary**: Still shows the standard summary statistics
- **Markdown report**: Saves to `./reports/scan_{org}_{timestamp}.md` with formatted tables and clickable links

### JSON Reports (default output)

- **Location**: `./reports/scan_{org}_{timestamp}.json`
- **Complete data**: All repositories with full metrics
- **Stale branches**: Complete list of orphaned branches (no limits)
- **Structured format**: Easy to parse and analyze
- **Generated when**: Running without `--pretty` flag

### Example Console Output (Default)

```
============================================================
GitHub Org: your-org
Scan Time: 2025-08-06 12:00:00
============================================================

Total repos: 96
Active repos (last year): 72

problematic-repo
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

### Example Pretty Table Output (Console)

```
====================================================================================================
DETAILED REPORT - STALE PRs AND ORPHANED BRANCHES
====================================================================================================

Repository                     | Type             | Item                      | User/Author          | Age        | Link
----------------------------------------------------------------------------------------------------
my-backend-api                 | Stale PR         | PR #123                   | john.doe             | 45 days    | https://github.com/org/my-backend-api/pull/123
my-backend-api                 | Orphaned Branch  | feature/old-feature       | jane.smith           | -          | https://github.com/org/my-backend-api/tree/feature/old-feature
frontend-app                   | Stale PR         | PR #87                    | bob.jones            | 62 days    | https://github.com/org/frontend-app/pull/87
frontend-app                   | Orphaned Branch  | bugfix/legacy-fix         | alice.williams       | -          | https://github.com/org/frontend-app/tree/bugfix/legacy-fix

Total items: 4
====================================================================================================
```

### Example Markdown Report (`.md` file)

The Markdown report includes:
- **Header**: Organization/repo name, scan time, threshold settings
- **Summary section**: Key metrics (total repos, active repos, repos with issues, total PRs)
- **Stale PRs and Orphaned Branches table**: Formatted Markdown table with clickable links
- **Repository Details section**: Detailed breakdown of each problematic repository

The Markdown file can be:
- Viewed directly in GitHub with proper formatting
- Shared with team members via email or chat
- Automatically uploaded to Discord via GitHub Actions
- Converted to PDF or other formats
- Included in documentation or reports

### Closed/Merged PR Branches Section

The report now includes a dedicated section for branches that still exist even though their PRs have been closed or merged:
- **Branch name**: The name of the branch that should be deleted
- **PR number and link**: Direct link to the closed/merged PR
- **User**: Who created the PR
- **Status**: Whether the PR was merged (🟣) or just closed (🔴)
- **Days since closed**: How long ago the PR was closed
- **Recommendation**: These branches are safe to delete

## GitHub Actions Workflow

The repository includes a GitHub Actions workflow that:
- Automatically scans organizations on push to `scan` branch
- Can be triggered manually with custom organization and threshold
- Generates Markdown reports with pretty formatting
- Uploads reports to Discord webhook automatically
- Saves reports as GitHub Actions artifacts (30-day retention)

### Workflow Triggers

1. **Push to `scan` branch**: Automatically runs the scan
2. **Manual trigger**: Run from GitHub Actions UI with custom inputs

### Discord Integration

The workflow automatically uploads the generated Markdown report to Discord:
- Report is posted as a file attachment
- Includes organization name in the message
- Webhook URL is configured in the workflow file

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
