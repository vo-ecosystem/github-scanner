#!/usr/bin/env python3
"""
GitHub Organization Repository Scanner
Runs in Docker container for isolation
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

class GitHubOrgScanner:
    def __init__(self, org_name, token=None):
        self.org_name = org_name
        self.base_url = "https://api.github.com"
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.headers["Authorization"] = f"token {token}"
        self.one_year_ago = datetime.now() - timedelta(days=365)
        self.old_pr_threshold_days = int(os.environ.get('OLD_PR_THRESHOLD_DAYS', '30'))
        self.report_data = []
    
    def make_request(self, url):
        """Make paginated requests to GitHub API."""
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
                print(f"Request failed: {e}", file=sys.stderr)
                break
        
        return all_items
    
    def get_org_repos(self):
        """Get all repositories in the organization."""
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
                'created_at': created_at.strftime("%Y-%m-%d")
            })
        
        # Get branches
        branches = self.get_branches(repo_name)
        branch_names = {b['name'] for b in branches}
        
        # Get branches with open PRs only (branches with closed/merged PRs are considered orphaned)
        open_pr_branches = self.get_open_pr_branches(repo_name)
        
        # Get default and protected branches to exclude
        default_branch = self.get_default_branch(repo_name)
        protected_branches = self.get_protected_branches(repo_name)
        
        # Calculate orphaned branches (exclude default and protected branches)
        excluded_branches = {default_branch} | protected_branches
        orphaned_branches = branch_names - open_pr_branches - excluded_branches
        
        return {
            'name': repo_name,
            'url': repo['html_url'],
            'open_prs': sorted(pr_info, key=lambda x: x['days_old'], reverse=True),
            'total_branches': len(branches),
            'branches_without_prs_count': len(orphaned_branches),
            'stale_branches': list(orphaned_branches)
        }
    
    def generate_report(self):
        """Generate the report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Console output
        print(f"\n{'='*60}")
        print(f"GitHub Org: {self.org_name}")
        print(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # Get repositories
        repos = self.get_org_repos()
        if not repos:
            print(f"ERROR: No repositories found or cannot access org '{self.org_name}'")
            sys.exit(1)
        
        print(f"Total repos: {len(repos)}")
        
        # Filter active repos
        active_repos = []
        for repo in repos:
            if self.check_recent_activity(repo):
                active_repos.append(repo)
        
        print(f"Active repos (last year): {len(active_repos)}\n")
        
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
                print(f"⚠️  {result['name']}")
                print(f"   Branches: {result['total_branches']} ({result['branches_without_prs_count']} orphaned)")
                
                if result['open_prs']:
                    old_prs = [pr for pr in result['open_prs'] if pr['days_old'] > self.old_pr_threshold_days]
                    if old_prs:
                        print(f"   Old PRs (>{self.old_pr_threshold_days}d): {len(old_prs)}")
                
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
        
        # Save JSON report
        report_path = f"./reports/scan_{self.org_name}_{timestamp}.json"
        os.makedirs("./reports", exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
            f.write('\n')  # Add blank line at end
        
        print(f"Full report saved: {report_path}")

def main():
    org_name = os.environ.get('GITHUB_ORG')
    token = os.environ.get('GITHUB_TOKEN')
    
    if not org_name:
        print("ERROR: GITHUB_ORG environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    if not token:
        print("WARNING: No GITHUB_TOKEN provided. API rate limits will be restrictive (60/hour).")
        print("Provide token for 5000 requests/hour.\n")
    
    scanner = GitHubOrgScanner(org_name, token)
    scanner.generate_report()

if __name__ == "__main__":
    main()
