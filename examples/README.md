# GitHub Scanner - External Usage Examples

This directory contains examples and documentation for using the GitHub Scanner from external repositories.

## Files

- `external-scan-workflow.yml` - GitHub Actions workflow for scanning repositories from external repos
- `README.md` - This documentation file

## External Workflow Usage

The `external-scan-workflow.yml` file provides a complete GitHub Actions workflow that can be used in any repository to scan either:
- An entire GitHub organization
- A specific repository

### Quick Setup

1. **Copy the workflow file** to your target repository:
   ```bash
   # In your external repository
   mkdir -p .github/workflows
   cp external-scan-workflow.yml .github/workflows/health-scan.yml
   ```

2. **Configure required secrets** in your repository settings:
   - Go to **Settings** → **Secrets and variables** → **Actions**
   - Add `GITHUB_TOKEN` with a personal access token that has repo access

3. **Optional: Enable issue creation**:
   - Go to **Settings** → **Secrets and variables** → **Variables**
   - Add `CREATE_ISSUE_ON_SCAN` with value `true`

### Manual Execution

1. Go to your repository's **Actions** tab
2. Select "External Repository Health Scan"
3. Click "Run workflow"
4. Configure parameters:
   - **Scan Mode**: Choose `org` (organization) or `repo` (single repository)
   - **Target Org**: Organization to scan (default: `vo-ecosystem`)
   - **Target Repo**: For single repo mode, format: `owner/repo`
   - **PR Threshold**: Days to consider PRs as old (default: 30)

### Scheduled Execution

The workflow automatically runs every Monday at 9 AM UTC. You can modify the cron schedule in the workflow file:

```yaml
on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM
```

## Usage Examples

### Example 1: Scan Entire Organization

**Use Case**: Monitor all repositories in the `vo-ecosystem` organization

**Configuration**:
- Scan Mode: `org`
- Target Org: `vo-ecosystem`
- Leave Target Repo empty

**Result**: Scans all repositories in the organization and generates a comprehensive health report.

### Example 2: Scan Specific Repository

**Use Case**: Monitor a single repository for health issues

**Configuration**:
- Scan Mode: `repo`
- Target Repo: `vo-ecosystem/github-scanner`
- Target Org: Can be left as default

**Result**: Scans only the specified repository.

### Example 3: Different Organization

**Use Case**: Monitor repositories in a different organization

**Configuration**:
- Scan Mode: `org`
- Target Org: `your-company`
- Adjust PR threshold if needed

**Result**: Scans all repositories in the specified organization.

### Example 4: Custom PR Threshold

**Use Case**: More sensitive detection of old PRs

**Configuration**:
- Any scan mode
- PR Threshold Days: `14` (instead of default 30)

**Result**: Reports PRs older than 14 days as requiring attention.

## Output and Results

### Artifacts

The workflow generates artifacts containing:
- JSON reports with detailed scan results
- Repository health metrics
- List of stale branches and old PRs

**Artifact Name**: `health-scan-report-{run_number}`
**Retention**: 30 days

### Optional Issue Creation

If `CREATE_ISSUE_ON_SCAN` is set to `true`, the workflow will automatically create an issue in the repository with:
- Scan summary statistics
- Links to detailed artifacts
- Actionable recommendations

### Report Structure

The JSON reports contain:
```json
{
  "summary": {
    "total_repositories": 25,
    "repositories_with_issues": 8,
    "total_stale_branches": 45,
    "total_old_prs": 12
  },
  "repositories": [
    {
      "name": "repo-name",
      "stale_branches": [...],
      "old_prs": [...],
      "health_score": 85
    }
  ]
}
```

## Customization

### Modifying Scan Parameters

Edit the workflow file to change:
- Default organization name
- Scan schedule
- Python version
- Report retention period

### Adding Custom Logic

The workflow can be extended to:
- Send notifications to Slack/Teams
- Create JIRA tickets for issues
- Generate custom reports
- Integrate with other tools

### Environment Variables

The scanner supports these environment variables:
- `GITHUB_TOKEN`: Required for API access
- `GITHUB_ORG`: Organization to scan
- `OLD_PR_THRESHOLD_DAYS`: Days threshold for old PRs
- `SINGLE_REPO`: For single repository scans

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure `GITHUB_TOKEN` has appropriate repository access
2. **Organization Not Found**: Verify the organization name is correct
3. **No Reports Generated**: Check if the organization has any repositories
4. **Workflow Fails**: Review the Actions logs for specific error messages

### Token Permissions

The GitHub token needs these permissions:
- `repo` - For accessing repository information
- `read:org` - For organization-level scanning

### Rate Limiting

For large organizations (100+ repos), the scanner:
- Implements automatic rate limiting
- Shows progress indicators
- May take several minutes to complete

## Support

For issues or questions:
1. Check the main repository documentation
2. Review the scanner.py source code
3. Create an issue in the vo-ecosystem/github-scanner repository
