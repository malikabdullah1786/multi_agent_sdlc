import os
import subprocess
import requests
import stat
import shutil
from pathlib import Path

_ROOT_DIR = Path(__file__).resolve().parents[3]

def push_to_github(repo_name: str, agent_name: str) -> dict:
    """
    Creates a GitHub repo via the API and pushes the output/ directory.
    Called generically by multiple agents.
    
    Args:
        repo_name (str): Name of the GitHub repo to push to.
        agent_name (str): The name of the agent doing the push (for commit message).
    """
    if not repo_name:
        print(f"[{agent_name}] No github_repo_name set. Skipping GitHub push.")
        return {}
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print(f"[{agent_name}] GITHUB_TOKEN not found in environment. Skipping GitHub push.")
        return {}
    
    output_dir = _ROOT_DIR / "output"
    if not output_dir.exists():
        print(f"[{agent_name}] No output directory found. Skipping GitHub push.")
        return {}
    
    # Step 1: Create the repo via GitHub API
    print(f"\n[{agent_name}] Creating/Verifying repository: {repo_name}...")
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    api_res = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json={"name": repo_name, "private": False, "auto_init": False}
    )
    
    if api_res.status_code == 201:
        clone_url = api_res.json().get("clone_url")
        print(f"[{agent_name}] Repository created: {clone_url}")
    elif api_res.status_code == 422:
        print(f"[{agent_name}] Repository already exists. Re-using.")
        user_res = requests.get("https://api.github.com/user", headers=headers)
        user_login = user_res.json().get("login")
        clone_url = f"https://github.com/{user_login}/{repo_name}.git"
    else:
        print(f"[{agent_name}] Failed to create repo: {api_res.status_code} {api_res.text}")
        return {}
    
    # Step 2: Remove any stale .git directory to avoid conflicts
    git_dir = output_dir / ".git"
    if git_dir.exists():
        def _force_remove(func, path, exc_info):
            """Handle Windows read-only files inside .git"""
            os.chmod(path, stat.S_IWRITE)
            func(path)
        try:
            shutil.rmtree(git_dir, onexc=_force_remove)
            print(f"[{agent_name}] Cleared stale .git directory.")
        except Exception:
            # Fallback: use Windows rmdir command
            subprocess.run(f'rmdir /s /q "{git_dir}"', shell=True, capture_output=True)
            print(f"[{agent_name}] Cleared stale .git directory (fallback).")
    
    import time
    
    # Step 3: Git init, add, commit
    auth_url = clone_url.replace("https://", f"https://{github_token}@")
    branch_name = f"feature/{agent_name.lower().replace(' ', '-')}-{int(time.time())}"
    
    # Create an initial commit if the repo is empty so we have a main branch
    # then checkout a new branch for this agent's changes
    git_commands = [
        "git init",
        "git checkout -b main",
        "git add .",
        f'git commit -m "Initial commit" || echo "No changes"',
        f"git push {auth_url} main || echo 'Already pushed main'",
        f"git checkout -b {branch_name}",
        "git add .",
        f'git commit -m "Progress commit by {agent_name}"',
        f"git push -u {auth_url} {branch_name}"
    ]
    
    for cmd in git_commands:
        safe_cmd = cmd.replace(github_token, "***")
        try:
            subprocess.run(cmd, shell=True, cwd=str(output_dir), capture_output=True, text=True, check=True)
            print(f"[{agent_name}] ✓ {safe_cmd}")
        except subprocess.CalledProcessError as e:
            safe_err = e.stderr.replace(github_token, "***")
            print(f"[{agent_name}] ✗ {safe_cmd}: {safe_err}")
    
    # Step 4: Create a Pull Request via GitHub API
    print(f"\n[{agent_name}] Creating Pull Request...")
    # Extract owner from user_login we fetched earlier, or just use the API to get user info if not fetched
    if 'user_login' not in locals() or not user_login:
        user_res = requests.get("https://api.github.com/user", headers=headers)
        user_login = user_res.json().get("login")
        
    pr_data = {
        "title": f"Code Updates from {agent_name}",
        "body": f"Automated PR created by {agent_name}. Please review.",
        "head": branch_name,
        "base": "main"
    }
    
    pr_res = requests.post(
        f"https://api.github.com/repos/{user_login}/{repo_name}/pulls",
        headers=headers,
        json=pr_data
    )
    
    if pr_res.status_code == 201:
        pr_json = pr_res.json()
        pr_number = pr_json.get("number")
        pr_url = pr_json.get("html_url")
        print(f"[{agent_name}] ✓ Pull Request created: #{pr_number} ({pr_url})")
        return {"pr_number": pr_number, "pr_url": pr_url}
    elif pr_res.status_code == 422:
        # A PR might already exist for this branch, though unlikely due to timestamp
        print(f"[{agent_name}] Pull Request creation failed or already exists: {pr_res.text}")
        return {}
    else:
        print(f"[{agent_name}] Failed to create PR: {pr_res.status_code} {pr_res.text}")
        return {}
