import os
import subprocess
from typing import List, Dict, Any, Optional

class GitService:
    @staticmethod
    def get_git_diff(repo_path: str = ".") -> str:
        """Returns the unified git diff for unstaged and staged changes in repo_path."""
        try:
            res = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10
            )
            if res.returncode == 0:
                return res.stdout
            # Fallback to unstaged diff
            res_unstaged = subprocess.run(
                ["git", "diff"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10
            )
            return res_unstaged.stdout
        except Exception as e:
            return f"Error fetching git diff: {str(e)}"

    @staticmethod
    def get_file_diff(file_path: str, repo_path: str = ".") -> str:
        """Returns git diff for a specific file path."""
        try:
            res = subprocess.run(
                ["git", "diff", "HEAD", "--", file_path],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10
            )
            return res.stdout if res.returncode == 0 else ""
        except Exception:
            return ""

    @staticmethod
    def list_file_tree(base_dir: str = ".") -> List[Dict[str, Any]]:
        """Returns a directory tree structure excluding ignored folders (.git, __pycache__, node_modules, etc.)."""
        tree = []
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", ".next", "dist", "build"}
        
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            rel_root = os.path.relpath(root, base_dir)
            
            for file in files:
                rel_file_path = os.path.normpath(os.path.join(rel_root, file)) if rel_root != "." else file
                full_path = os.path.join(root, file)
                try:
                    stat = os.stat(full_path)
                    tree.append({
                        "path": rel_file_path.replace("\\", "/"),
                        "size": stat.st_size,
                        "modified_at": stat.st_mtime
                    })
                except Exception:
                    pass
        return tree
