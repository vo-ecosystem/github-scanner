#!/usr/bin/env python3
"""
GitHub Organization Repository Scanner
Runs in Docker container for isolation
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
from collections import defaultdict

class GitHubOrgScanner:
    def __init__(self, org_name, token=None, pretty_print=False, delete_branches=False, delete_prs=False):
        self.org_name = org_name
        self.base_url = "https://api.github.com"
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.headers["Authorization"] = f"token {token}"
        self.one_year_ago = datetime.now() - timedelta(days=365)
        self.old_pr_threshold_days = int(os.environ.get('OLD_PR_THRESHOLD_DAYS', '30'))
        self.single_repo = os.environ.get('GITHUB_REPO')  # If set, scan only this repo
        self.delete_orphaned_branches = os.environ.get('DELETE_ORPHANED_BRANCHES', 'false').lower() == 'true'
        self.report_data = []
        self.pretty_print = pretty_print
        self.delete_branches = delete_branches
        self.delete_prs = delete_prs
    
    def make_request(self, url, retry_on_403=True):
        """Make a request to the GitHub API with pagination support."""
        all_items = []
        
        while url:
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                all_items.extend(response.json())
                
                # Handle pagination
                links = response.headers.get('Link', '')
                url = None
                if links:
                    for link in links.split(','):
                        if 'rel="next"' in link:
                            url = link.split('<')[1].split('>')[0]
                            break
            except requests.exceptions.RequestException as e:
                # Retry once on 403 errors after a delay
                if '403' in str(e) and retry_on_403:
                    time.sleep(5)
                    return self.make_request(url, retry_on_403=False)
                
                # Silently skip 403/404 errors after retry
                if '403' not in str(e) and '404' not in str(e):
                    print(f"Request failed: {e}", file=sys.stderr)
                break
        
        return all_items
    
    def get_single_repo(self, repo_name):
        """Get a single repository by name."""
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                return [response.json()]  # Return as list for consistency
            else:
                print(f"ERROR: Repository '{repo_name}' not found or not accessible", file=sys.stderr)
                return []
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to get repository '{repo_name}': {e}", file=sys.stderr)
            return []
    
    def get_org_repos(self):
        """Get all repositories in the organization or single repo if REPO_NAME is set."""
        if self.single_repo:
            return self.get_single_repo(self.single_repo)
        
        url = f"{self.base_url}/orgs/{self.org_name}/repos?per_page=100&type=all"
        return self.make_request(url)
    
    def check_recent_activity(self, repo):
        """Check if repo has commits in the last year."""
        url = f"{self.base_url}/repos/{self.org_name}/{repo['name']}/commits"
        url += f"?since={self.one_year_ago.isoformat()}&per_page=1"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            return len(response.json()) > 0 if response.status_code == 200 else False
        except:
            return False
    
    def get_open_prs(self, repo_name):
        """Get open PRs for a repository."""
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}/pulls?state=open&per_page=100"
        return self.make_request(url)
    
    def get_branches(self, repo_name):
        """Get all branches for a repository."""
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}/branches?per_page=100"
        return self.make_request(url)
    
    def get_all_pr_branches(self, repo_name):
        """Get branches that have associated PRs (open, closed, merged)."""
        pr_branches = set()
        
        # Get all PRs (open and closed) in one request - more efficient
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}/pulls?state=all&per_page=100"
        prs = self.make_request(url)
        for pr in prs:
            if pr.get('head', {}).get('ref'):
                pr_branches.add(pr['head']['ref'])
        
        return pr_branches
    
    def get_open_pr_branches(self, repo_name):
        """Get branches that have open PRs only."""
        open_pr_branches = set()
        
        # Get only open PRs
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}/pulls?state=open&per_page=100"
        prs = self.make_request(url)
        for pr in prs:
            if pr.get('head', {}).get('ref'):
                open_pr_branches.add(pr['head']['ref'])
        
        return open_pr_branches
    
    def get_closed_merged_pr_branches(self, repo_name):
        """Get branches with closed/merged PRs and their details."""
        closed_merged_branches = []
        
        # Get closed PRs
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}/pulls?state=closed&per_page=100"
        prs = self.make_request(url)
        
        for pr in prs:
            if pr.get('head', {}).get('ref'):
                branch_name = pr['head']['ref']
                closed_at = pr.get('closed_at')
                merged_at = pr.get('merged_at')
                
                if closed_at:
                    closed_date = datetime.strptime(closed_at, "%Y-%m-%dT%H:%M:%SZ")
                    days_since_closed = (datetime.now() - closed_date).days
                    
                    closed_merged_branches.append({
                        'branch': branch_name,
                        'pr_number': pr['number'],
                        'pr_url': pr['html_url'],
                        'user': pr['user']['login'] if pr.get('user') else 'Unknown',
                        'status': 'merged' if merged_at else 'closed',
                        'closed_at': closed_date.strftime("%Y-%m-%d"),
                        'days_since_closed': days_since_closed
                    })
        
        return closed_merged_branches
    
    def delete_branch(self, repo_name, branch_name):
        """Delete a branch from a repository."""
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}/git/refs/heads/{branch_name}"
        try:
            response = requests.delete(url, headers=self.headers, timeout=30)
            if response.status_code == 204:
                return True, "Deleted successfully"
            elif response.status_code == 404:
                return False, "Not found"
            elif response.status_code == 422:
                # Try to get more details from response
                try:
                    error_data = response.json()
                    message = error_data.get('message', '')
                    
                    # Common 422 reasons
                    if 'protected' in message.lower():
                        return False, "Protected branch"
                    elif 'required' in message.lower():
                        return False, "Required by rules"
                    elif 'open pull request' in message.lower() or 'reference' in message.lower():
                        return False, "Has open PR"
                    else:
                        # Return the actual GitHub message
                        return False, message[:40] if message else "Cannot delete"
                except:
                    return False, "Cannot delete (422)"
            elif response.status_code == 403:
                return False, "Permission denied"
            else:
                return False, f"HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Error: {str(e)[:20]}"
    
    def close_pr(self, repo_name, pr_number):
        """Close a pull request."""
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}/pulls/{pr_number}"
        try:
            response = requests.patch(url, headers=self.headers, json={"state": "closed"}, timeout=30)
            if response.status_code == 200:
                return True, "Closed successfully"
            else:
                return False, f"Failed: {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Error: {e}"
    
    def get_default_branch(self, repo_name):
        """Get the default branch for a repository."""
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                repo_data = response.json()
                return repo_data.get('default_branch', 'main')
        except requests.exceptions.RequestException as e:
            print(f"Failed to get default branch for {repo_name}: {e}", file=sys.stderr)
        return 'main'  # fallback
    
    def get_protected_branches(self, repo_name):
        """Get protected branches for a repository."""
        protected_branches = set()
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}/branches"
        try:
            branches = self.make_request(url)
            for branch in branches:
                if branch.get('protected', False):
                    protected_branches.add(branch['name'])
        except requests.exceptions.RequestException as e:
            print(f"Failed to get protected branches for {repo_name}: {e}", file=sys.stderr)
        return protected_branches
    
    def get_branch_last_commit_author(self, repo_name, branch_name):
        """Get the last commit author for a branch."""
        url = f"{self.base_url}/repos/{self.org_name}/{repo_name}/commits/{branch_name}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                commit_data = response.json()
                author = commit_data.get('commit', {}).get('author', {})
                return author.get('name', 'Unknown')
        except:
            pass
        return 'Unknown'
    
    def analyze_repo(self, repo):
        """Analyze a single repository."""
        repo_name = repo['name']
        
        # Get open PRs
        open_prs = self.get_open_prs(repo_name)
        pr_info = []
        for pr in open_prs:
            created_at = datetime.strptime(pr['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            days_old = (datetime.now() - created_at).days
            pr_info.append({
                'number': pr['number'],
                'days_old': days_old,
                'created_at': created_at.strftime("%Y-%m-%d"),
                'url': pr['html_url'],
                'user': pr['user']['login'] if pr.get('user') else 'Unknown'
            })
        
        # Get branches
        branches = self.get_branches(repo_name)
        branch_names = {b['name'] for b in branches}
        
        # Get branches with open PRs only (branches with closed/merged PRs are considered orphaned)
        open_pr_branches = self.get_open_pr_branches(repo_name)
        
        # Get closed/merged PR branches
        closed_merged_pr_branches = self.get_closed_merged_pr_branches(repo_name)
        
        # Filter to only include branches that still exist
        closed_merged_existing = [b for b in closed_merged_pr_branches if b['branch'] in branch_names]
        
        # Standard branches that should never be deleted
        standard_branches = {
            'main', 'master', 'develop', 'development', 'dev',
            'staging', 'stage', 'prod', 'production',
            'test', 'testing', 'qa', 'uat', 'preprod', 'pre-prod',
            'release', 'hotfix', 'stable'
        }
        
        # Deduplicate by branch name (keep the most recent PR for each branch)
        # Also exclude standard branches and branches with open PRs
        branch_dict = {}
        for b in closed_merged_existing:
            branch_name = b['branch']
            
            # Skip standard branches
            if branch_name.lower() in standard_branches:
                continue
            
            # Skip branches that are part of an open PR
            if branch_name in open_pr_branches:
                continue
                
            if branch_name not in branch_dict:
                branch_dict[branch_name] = b
            else:
                # Keep the one with the most recent closure
                existing_days = branch_dict[branch_name]['days_since_closed']
                if b['days_since_closed'] < existing_days:
                    branch_dict[branch_name] = b
        
        closed_merged_unique = list(branch_dict.values())
        
        # Delete orphaned branches with closed/merged PRs if enabled
        deletion_results = []
        if self.delete_orphaned_branches and closed_merged_unique:
            print(f"\n  Deleting {len(closed_merged_unique)} orphaned branches with closed/merged PRs...")
            for branch_info in closed_merged_unique:
                success, msg = self.delete_branch(repo_name, branch_info['branch'])
                status = "✓" if success else "✗"
                print(f"  {status} {branch_info['branch']}: {msg}")
                
                # Track deletion results
                deletion_results.append({
                    'branch': branch_info['branch'],
                    'pr_number': branch_info['pr_number'],
                    'pr_url': branch_info['pr_url'],
                    'user': branch_info['user'],
                    'status': branch_info['status'],
                    'closed_at': branch_info['closed_at'],
                    'days_since_closed': branch_info['days_since_closed'],
                    'deletion_success': success,
                    'deletion_message': msg
                })
        
        # Get default and protected branches to exclude
        default_branch = self.get_default_branch(repo_name)
        protected_branches = self.get_protected_branches(repo_name)
        
        # Standard branches that should never be deleted
        standard_branches = {
            'main', 'master', 'develop', 'development', 'dev',
            'staging', 'stage', 'prod', 'production',
            'test', 'testing', 'qa', 'uat', 'preprod', 'pre-prod',
            'release', 'hotfix', 'stable'
        }
        
        # Calculate orphaned branches (exclude default, protected, and standard branches)
        excluded_branches = {default_branch} | protected_branches | standard_branches
        orphaned_branches = branch_names - open_pr_branches - excluded_branches
        
        # Get branch details with authors if pretty print is enabled
        orphaned_branch_details = []
        if self.pretty_print:
            for branch_name in orphaned_branches:
                # Skip if this branch has a closed/merged PR (we'll show it separately)
                if any(b['branch'] == branch_name for b in closed_merged_unique):
                    continue
                author = self.get_branch_last_commit_author(repo_name, branch_name)
                orphaned_branch_details.append({
                    'name': branch_name,
                    'author': author
                })
        
        return {
            'name': repo_name,
            'url': repo['html_url'],
            'open_prs': sorted(pr_info, key=lambda x: x['days_old'], reverse=True),
            'total_branches': len(branches),
            'branches_without_prs_count': len(orphaned_branches),
            'stale_branches': list(orphaned_branches),
            'orphaned_branch_details': orphaned_branch_details,
            'closed_merged_pr_branches': closed_merged_unique if not self.delete_orphaned_branches else [],
            'deleted_branches': deletion_results
        }
    
    def generate_report(self):
        """Generate the report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Console output
        print(f"\n{'='*60}")
        if self.single_repo:
            print(f"GitHub Repo: {self.org_name}/{self.single_repo}")
        else:
            print(f"GitHub Org: {self.org_name}")
        print(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # Get repositories
        repos = self.get_org_repos()
        if not repos:
            if self.single_repo:
                print(f"ERROR: Repository '{self.single_repo}' not found or not accessible in org '{self.org_name}'")
            else:
                print(f"ERROR: No repositories found or cannot access org '{self.org_name}'")
            sys.exit(1)
        
        print(f"Total repos: {len(repos)}")
        
        # Filter active repos and exclude archived repos
        active_repos = []
        archived_count = 0
        inactive_count = 0
        
        for repo in repos:
            if repo.get('archived', False):
                archived_count += 1
                continue
            if self.check_recent_activity(repo):
                active_repos.append(repo)
            else:
                inactive_count += 1
        
        print(f"Active repos (last year): {len(active_repos)}")
        print(f"Archived repos (skipped): {archived_count}")
        print(f"Inactive repos (skipped): {inactive_count}\n")
        
        if not active_repos:
            print("No active repositories found.")
            return
        
        # Analyze each repo
        summary = {
            'total_repos': len(repos),
            'active_repos': len(active_repos),
            'repos_with_issues': 0,
            'total_open_prs': 0,
            'repos': []
        }
        
        for i, repo in enumerate(active_repos, 1):
            print(f"\rAnalyzing repos: {i}/{len(active_repos)} - {repo['name']}", end='', flush=True)
            result = self.analyze_repo(repo)
            summary['repos'].append(result)
            summary['total_open_prs'] += len(result['open_prs'])
            
            # Check for issues
            has_issues = (len(result['open_prs']) > 3 or 
                         any(pr['days_old'] > self.old_pr_threshold_days for pr in result['open_prs']) or
                         result['branches_without_prs_count'] > 0)
            
            if has_issues:
                summary['repos_with_issues'] += 1
            
            # Console output for problematic repos only
            if has_issues:
                # Clear progress line before showing problematic repo
                print(f"\r{' ' * 80}\r", end='')  # Clear the progress line
                print(f"WARNING: {result['name']}")
                print(f"   Branches: {result['total_branches']} ({result['branches_without_prs_count']} orphaned)")
                
                if result['open_prs']:
                    old_prs = [pr for pr in result['open_prs'] if pr['days_old'] > self.old_pr_threshold_days]
                    if old_prs:
                        print(f"   Old PRs (>{self.old_pr_threshold_days}d): {len(old_prs)}")
                        
                        # Delete stale PRs if in delete mode
                        if self.delete_prs:
                            print(f"\n  Closing {len(old_prs)} stale PRs...")
                            for pr in old_prs:
                                success, msg = self.close_pr(result['name'], pr['number'])
                                status = "✓" if success else "✗"
                                print(f"  {status} PR #{pr['number']}: {msg}")
                
                # Delete orphaned branches if in delete mode
                if self.delete_branches and result['branches_without_prs_count'] > 0:
                    print(f"\n  Deleting {result['branches_without_prs_count']} orphaned branches...")
                    for branch_name in result['stale_branches']:
                        success, msg = self.delete_branch(result['name'], branch_name)
                        status = "✓" if success else "✗"
                        print(f"  {status} {branch_name}: {msg}")
                
                print()
        
        # Clear any remaining progress line
        print(f"\r{' ' * 80}\r", end='')
        
        # Summary
        print(f"\n{'='*60}")
        print(f"SUMMARY:")
        print(f"• Total repos: {summary['total_repos']}")
        print(f"• Active repos (last year): {summary['active_repos']}")
        print(f"• Repos with issues: {summary['repos_with_issues']}")
        print(f"• Total open PRs: {summary['total_open_prs']}")
        print(f"• Repos needing attention listed above")
        print(f"{'='*60}\n")
        
        # Save reports
        os.makedirs("./reports", exist_ok=True)
        
        if self.pretty_print:
            # Save Markdown report for pretty output
            if self.single_repo:
                report_path = f"./reports/scan_{self.org_name}_{self.single_repo}_{timestamp}.md"
            else:
                report_path = f"./reports/scan_{self.org_name}_{timestamp}.md"
            
            self.save_markdown_report(summary, report_path, timestamp)
            print(f"Full report saved: {report_path}")
            
            # Also print to console
            self.print_pretty_table(summary)
        else:
            # Save JSON report for default output
            if self.single_repo:
                report_path = f"./reports/scan_{self.org_name}_{self.single_repo}_{timestamp}.json"
            else:
                report_path = f"./reports/scan_{self.org_name}_{timestamp}.json"
            
            with open(report_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
                f.write('\n')  # Add blank line at end
            
            print(f"Full report saved: {report_path}")
    
    def collect_table_rows(self, summary):
        """Collect all table rows for stale PRs and orphaned branches."""
        table_rows = []
        
        for repo in summary['repos']:
            repo_name = repo['name']
            
            # Add stale PRs (older than threshold)
            for pr in repo['open_prs']:
                if pr['days_old'] > self.old_pr_threshold_days:
                    table_rows.append({
                        'repo': repo_name,
                        'type': 'Stale PR',
                        'item': f"PR #{pr['number']}",
                        'link': pr['url'],
                        'user': pr['user'],
                        'age': f"{pr['days_old']} days"
                    })
            
            # Add orphaned branches
            for branch_detail in repo.get('orphaned_branch_details', []):
                table_rows.append({
                    'repo': repo_name,
                    'type': 'Orphaned Branch',
                    'item': branch_detail['name'],
                    'link': f"https://github.com/{self.org_name}/{repo_name}/tree/{branch_detail['name']}",
                    'user': branch_detail['author'],
                    'age': '-'
                })
        
        return table_rows
    
    def save_markdown_report(self, summary, report_path, timestamp):

        """Save a Markdown report with pretty formatting."""
        table_rows = self.collect_table_rows(summary)
        
        # Collect closed/merged PR branches or deletion results
        closed_merged_rows = []
        deleted_branches_rows = []
        
        for repo in summary['repos']:
            repo_name = repo['name']
            
            # Collect deletion results if DELETE_ORPHANED_BRANCHES was enabled
            for branch in repo.get('deleted_branches', []):
                deleted_branches_rows.append({
                    'repo': repo_name,
                    'branch': branch['branch'],
                    'pr_number': branch['pr_number'],
                    'pr_url': branch['pr_url'],
                    'user': branch['user'],
                    'status': branch['status'],
                    'closed_at': branch['closed_at'],
                    'days_since_closed': branch['days_since_closed'],
                    'deletion_success': branch['deletion_success'],
                    'deletion_message': branch['deletion_message']
                })
            
            # Collect branches that still exist (only if not in deletion mode)
            for branch in repo.get('closed_merged_pr_branches', []):
                closed_merged_rows.append({
                    'repo': repo_name,
                    'branch': branch['branch'],
                    'pr_number': branch['pr_number'],
                    'pr_url': branch['pr_url'],
                    'user': branch['user'],
                    'status': branch['status'],
                    'closed_at': branch['closed_at'],
                    'days_since_closed': branch['days_since_closed']
                })
        
        with open(report_path, 'w') as f:
            # Header
            f.write(f"# GitHub Repository Health Report\n\n")
            if self.single_repo:
                f.write(f"**Repository:** {self.org_name}/{self.single_repo}\n\n")
            else:
                f.write(f"**Organization:** {self.org_name}\n\n")
            f.write(f"**Scan Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Old PR Threshold:** {self.old_pr_threshold_days} days\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(f"- **Total repositories:** {summary['total_repos']}\n")
            f.write(f"- **Active repositories (last year):** {summary['active_repos']}\n")
            f.write(f"- **Repositories with issues:** {summary['repos_with_issues']}\n")
            f.write(f"- **Total open PRs:** {summary['total_open_prs']}\n")
            
            if deleted_branches_rows:
                successful_deletions = sum(1 for b in deleted_branches_rows if b['deletion_success'])
                failed_deletions = len(deleted_branches_rows) - successful_deletions
                f.write(f"- **Branches deleted:** {successful_deletions} (Failed: {failed_deletions})\n\n")
            else:
                f.write(f"- **Branches with closed/merged PRs:** {len(closed_merged_rows)}\n\n")
            
            # Detailed table
            f.write("## Stale PRs and Orphaned Branches\n\n")
            
            if not table_rows:
                f.write("✅ No stale PRs or orphaned branches found.\n\n")
            else:
                # Markdown table
                f.write("| Repository | Type | Item | User/Author | Age | Link |\n")
                f.write("|------------|------|------|-------------|-----|------|\n")
                
                for row in table_rows:
                    f.write(f"| {row['repo']} | {row['type']} | {row['item']} | {row['user']} | {row['age']} | [View]({row['link']}) |\n")
                
                f.write(f"\n**Total items:** {len(table_rows)}\n\n")
            
            # Deleted Branches section (if deletion was enabled)
            if deleted_branches_rows:
                f.write("## Deleted Branches (Closed/Merged PRs)\n\n")
                f.write("These branches were automatically deleted because their PRs were closed or merged.\n\n")
                
                # Markdown table
                f.write("| Repository | Branch | PR | User | PR Status | Closed Date | Days Since | Deletion | Link |\n")
                f.write("|------------|--------|----|----- |-----------|-------------|------------|----------|------|\n")
                
                for row in deleted_branches_rows:
                    status_emoji = "🟣" if row['status'] == 'merged' else "🔴"
                    deletion_emoji = "✅" if row['deletion_success'] else "❌"
                    deletion_status = "Deleted" if row['deletion_success'] else f"Failed: {row['deletion_message']}"
                    f.write(f"| {row['repo']} | {row['branch']} | PR #{row['pr_number']} | {row['user']} | {status_emoji} {row['status'].title()} | {row['closed_at']} | {row['days_since_closed']} days | {deletion_emoji} {deletion_status} | [View]({row['pr_url']}) |\n")
                
                successful = sum(1 for b in deleted_branches_rows if b['deletion_success'])
                failed = len(deleted_branches_rows) - successful
                f.write(f"\n**Total:** {len(deleted_branches_rows)} branches ({successful} deleted, {failed} failed)\n\n")
            
            # Closed/Merged PR Branches section (only if deletion was NOT enabled)
            elif closed_merged_rows:
                f.write("## Branches with Closed/Merged PRs\n\n")
                f.write("These branches still exist but their PRs have been closed or merged. Consider deleting them.\n\n")
                
                # Markdown table
                f.write("| Repository | Branch | PR | User | Status | Closed Date | Days Since | Link |\n")
                f.write("|------------|--------|----|----- |--------|-------------|------------|------|\n")
                
                for row in closed_merged_rows:
                    status_emoji = "🟣" if row['status'] == 'merged' else "🔴"
                    f.write(f"| {row['repo']} | {row['branch']} | PR #{row['pr_number']} | {row['user']} | {status_emoji} {row['status'].title()} | {row['closed_at']} | {row['days_since_closed']} days | [View]({row['pr_url']}) |\n")
                
                f.write(f"\n**Total branches:** {len(closed_merged_rows)}\n\n")
            else:
                f.write("## Branches with Closed/Merged PRs\n\n")
                f.write("✅ No branches with closed/merged PRs found.\n\n")
            
            # Repository details
            f.write("## Repository Details\n\n")
            for repo in summary['repos']:
                has_issues = (len(repo['open_prs']) > 3 or 
                             any(pr['days_old'] > self.old_pr_threshold_days for pr in repo['open_prs']) or
                             repo['branches_without_prs_count'] > 0)
                
                if has_issues:
                    f.write(f"### {repo['name']}\n\n")
                    f.write(f"- **Repository URL:** [{repo['url']}]({repo['url']})\n")
                    f.write(f"- **Total branches:** {repo['total_branches']}\n")
                    f.write(f"- **Orphaned branches:** {repo['branches_without_prs_count']}\n")
                    f.write(f"- **Open PRs:** {len(repo['open_prs'])}\n")
                    
                    old_prs = [pr for pr in repo['open_prs'] if pr['days_old'] > self.old_pr_threshold_days]
                    if old_prs:
                        f.write(f"- **Old PRs (>{self.old_pr_threshold_days}d):** {len(old_prs)}\n")
                    
                    f.write("\n")
    
    def print_pretty_table(self, summary):
        """Print a human-friendly table of stale PRs and orphaned branches."""
        print(f"\n{'='*100}")
        print("DETAILED REPORT - STALE PRs AND ORPHANED BRANCHES")
        print(f"{'='*100}\n")
        
        table_rows = self.collect_table_rows(summary)
        
        if not table_rows:
            print("No stale PRs or orphaned branches found.\n")
        else:
            # Print table header
            header = f"{'Repository':<30} | {'Type':<16} | {'Item':<25} | {'User/Author':<20} | {'Age':<10} | {'Link'}"
            print(header)
            print("-" * len(header))
            
            # Print table rows
            for row in table_rows:
                repo_col = row['repo'][:29] if len(row['repo']) > 29 else row['repo']
                item_col = row['item'][:24] if len(row['item']) > 24 else row['item']
                user_col = row['user'][:19] if len(row['user']) > 19 else row['user']
                
                print(f"{repo_col:<30} | {row['type']:<16} | {item_col:<25} | {user_col:<20} | {row['age']:<10} | {row['link']}")
            
            print(f"\nTotal items: {len(table_rows)}")
        
        # Print deleted branches or closed/merged PR branches
        print(f"\n{'='*100}")
        
        # Check if we have deletion results
        deleted_count = sum(len(repo.get('deleted_branches', [])) for repo in summary['repos'])
        
        if deleted_count > 0:
            print("DELETED BRANCHES (CLOSED/MERGED PRs)")
            print(f"{'='*100}\n")
            
            total_deleted = 0
            successful = 0
            failed = 0
            
            for repo in summary['repos']:
                for branch in repo.get('deleted_branches', []):
                    if total_deleted == 0:
                        # Print header
                        header = f"{'Repository':<30} | {'Branch':<25} | {'PR':<10} | {'Status':<10} | {'Deletion':<15} | {'Link'}"
                        print(header)
                        print("-" * len(header))
                    
                    repo_col = repo['name'][:29] if len(repo['name']) > 29 else repo['name']
                    branch_col = branch['branch'][:24] if len(branch['branch']) > 24 else branch['branch']
                    pr_col = f"#{branch['pr_number']}"
                    status_col = branch['status'].title()
                    
                    if branch['deletion_success']:
                        deletion_col = "✅ Deleted"
                        successful += 1
                    else:
                        deletion_col = f"❌ {branch['deletion_message'][:10]}"
                        failed += 1
                    
                    print(f"{repo_col:<30} | {branch_col:<25} | {pr_col:<10} | {status_col:<10} | {deletion_col:<15} | {branch['pr_url']}")
                    total_deleted += 1
            
            print(f"\nTotal: {total_deleted} branches ({successful} deleted, {failed} failed)")
        else:
            print("BRANCHES WITH CLOSED/MERGED PRs")
            print(f"{'='*100}\n")
            
            closed_merged_count = 0
            for repo in summary['repos']:
                for branch in repo.get('closed_merged_pr_branches', []):
                    if closed_merged_count == 0:
                        # Print header
                        header = f"{'Repository':<30} | {'Branch':<25} | {'PR':<10} | {'User':<15} | {'Status':<10} | {'Days':<8} | {'Link'}"
                        print(header)
                        print("-" * len(header))
                    
                    repo_col = repo['name'][:29] if len(repo['name']) > 29 else repo['name']
                    branch_col = branch['branch'][:24] if len(branch['branch']) > 24 else branch['branch']
                    user_col = branch['user'][:14] if len(branch['user']) > 14 else branch['user']
                    pr_col = f"#{branch['pr_number']}"
                    status_col = branch['status'].title()
                    
                    print(f"{repo_col:<30} | {branch_col:<25} | {pr_col:<10} | {user_col:<15} | {status_col:<10} | {branch['days_since_closed']:<8} | {branch['pr_url']}")
                    closed_merged_count += 1
            
            if closed_merged_count == 0:
                print("No branches with closed/merged PRs found.\n")
            else:
                print(f"\nTotal branches: {closed_merged_count}")
        
        print(f"{'='*100}\n")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='GitHub Organization Repository Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '-p', '--pretty',
        action='store_true',
        help='Output a human-friendly table of stale PRs and orphaned branches'
    )
    parser.add_argument(
        '--delete-branches',
        action='store_true',
        help='Delete all orphaned branches (branches without open PRs)'
    )
    parser.add_argument(
        '--delete-prs',
        action='store_true',
        help='Close all stale PRs that exceed the threshold'
    )
    args = parser.parse_args()
    
    org_name = os.environ.get('GITHUB_ORG')
    token = os.environ.get('GITHUB_TOKEN')
    
    if not org_name:
        print("ERROR: GITHUB_ORG environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    if not token:
        print("WARNING: No GITHUB_TOKEN provided. API rate limits will be restrictive (60/hour).")
        print("Provide token for 5000 requests/hour.\n")
    
    # Warn if deletion modes are enabled
    if args.delete_branches:
        print("⚠️  WARNING: Branch deletion mode is ENABLED. Orphaned branches will be deleted!\n")
    if args.delete_prs:
        print("⚠️  WARNING: PR closure mode is ENABLED. Stale PRs will be closed!\n")
    
    scanner = GitHubOrgScanner(org_name, token, pretty_print=args.pretty, 
                               delete_branches=args.delete_branches, delete_prs=args.delete_prs)
    scanner.generate_report()

if __name__ == "__main__":
    main()
