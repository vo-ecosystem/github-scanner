# GitHub Scanner Pipeline Notes

This document explains the internal GitHub Actions workflow for the GitHub Scanner project.

## Workflow Overview

The `repo-health-scan.yml` workflow is designed to automatically scan GitHub organizations for repository health metrics. It provides flexible triggering options and intelligent organization detection.

## Trigger Methods

### 1. Push to `scan` Branch
The workflow automatically triggers when code is pushed to the `scan` branch:
```bash
git checkout -b scan
git push origin scan
```

### 2. Manual Trigger (workflow_dispatch)
The workflow can be manually triggered from the GitHub Actions UI with optional parameters:
- **github_org**: Override organization to scan
- **pr_threshold_days**: Days threshold for considering PRs as old (default: 30)

## GitHub Organization Detection

The workflow uses a **priority-based system** to determine which GitHub organization to scan:

### Priority Order:
1. **Manual Input** (highest priority)
   - When manually triggering the workflow, the `github_org` input overrides all other sources
   
2. **Commit Message**
   - If the latest commit message contains `GITHUB_ORG=organization-name`, it will use that organization
   - Example commit message: `"Fix scanner bug GITHUB_ORG=my-company"`
   
3. **Repository Secret** (fallback)
   - Uses the `GITHUB_ORG` secret configured in repository settings
   - Go to Settings → Secrets and variables → Actions → New repository secret

### Error Handling
If no organization is found through any of the above methods, the workflow will:
- Display clear error messages
- Provide instructions on how to configure the organization
- Exit with failure status

## Usage Examples

### Example 1: Using Commit Message
```bash
git add .
git commit -m "Update scanner configuration GITHUB_ORG=vo-ecosystem"
git push origin scan
```

### Example 2: Manual Trigger with Custom Organization
1. Go to Actions tab in GitHub
2. Select "Repository Health Scan"
3. Click "Run workflow"
4. Enter organization name in `github_org` field
5. Optionally adjust `pr_threshold_days`

### Example 3: Using Repository Secret
1. Set `GITHUB_ORG` secret to `vo-ecosystem` in repository settings
2. Push any commit to `scan` branch
3. Workflow will automatically use the secret value

## Workflow Steps

### 1. Checkout Code
- Fetches the complete git history (`fetch-depth: 0`)
- Required to access commit messages for organization detection

### 2. Determine GitHub Organization
- Executes the priority-based organization detection logic
- Sets the organization as an output variable for subsequent steps
- Provides clear logging of which source was used

### 3. Run GitHub Scanner
- Executes `make fresh` command with determined environment variables
- Uses the detected organization and configurable PR threshold
- Displays scan parameters for transparency

### 4. Upload Report
- Creates artifacts with scan results
- Artifact naming includes organization and run number for easy identification
- Sets 30-day retention period for reports

## Environment Variables

The workflow sets these environment variables for the scanner:

- `GITHUB_TOKEN`: Automatically provided by GitHub Actions
- `GITHUB_ORG`: Determined through the priority system described above
- `OLD_PR_THRESHOLD_DAYS`: From manual input or defaults to 30

## Artifacts

### Naming Convention
Artifacts are named: `health-report-{organization}-{run_number}`

Examples:
- `health-report-vo-ecosystem-123`
- `health-report-my-company-456`

### Contents
- JSON reports with detailed scan results
- Repository health metrics
- Lists of stale branches and old pull requests

### Retention
- Reports are retained for 30 days
- Can be downloaded from the Actions run page

## Security Considerations

### Token Permissions
The workflow uses the default `GITHUB_TOKEN` which has:
- Read access to the repository
- Access to organization repositories (if the token has appropriate permissions)

### Secrets Management
- `GITHUB_ORG` secret is optional but recommended for consistent scans
- Never hardcode sensitive information in commit messages
- Organization names are generally not sensitive, so commit message usage is acceptable

## Troubleshooting

### Common Issues

1. **"No GitHub organization specified" Error**
   - Solution: Set `GITHUB_ORG` secret or include it in commit message

2. **Permission Denied Errors**
   - Solution: Ensure the repository has access to scan the target organization
   - May require organization-level token or app installation

3. **Workflow Not Triggering on Push**
   - Verify you're pushing to the `scan` branch specifically
   - Check that the workflow file is in the default branch

4. **Commit Message Not Parsed**
   - Ensure format is exactly `GITHUB_ORG=organization-name`
   - No spaces around the equals sign
   - Organization name should not contain spaces

### Debugging Tips

1. **Check Workflow Logs**
   - The "Determine GitHub Organization" step shows which source was used
   - Look for clear messages about organization detection

2. **Verify Commit Messages**
   ```bash
   git log -1 --pretty=%B  # Shows the latest commit message
   ```

3. **Test Manual Trigger**
   - Use manual trigger to test with known organization
   - Helps isolate organization detection issues

## Best Practices

### For Development
- Use commit message method for testing different organizations
- Create feature branches and merge to `scan` branch for testing

### For Production
- Set `GITHUB_ORG` secret for consistent organization scanning
- Use manual triggers for ad-hoc scans of different organizations
- Monitor artifact retention and download important reports

### For CI/CD Integration
- The `scan` branch can be used as a deployment trigger
- Combine with other workflows for comprehensive repository management
- Consider scheduling regular pushes to `scan` branch for automated scanning

## Integration with Other Tools

The workflow can be extended to:
- Send notifications to Slack/Teams channels
- Create issues automatically for repositories with problems
- Generate summary reports for management
- Integrate with project management tools

## Maintenance

### Regular Updates
- Review and update the PR threshold based on team practices
- Monitor artifact storage usage
- Update Python dependencies in the scanner

### Monitoring
- Set up notifications for workflow failures
- Review scan results regularly
- Track trends in repository health over time
