import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import FileRecord
from backend.schemas import FileRecordResponse
from backend.git_service import GitService

router = APIRouter(prefix="/files", tags=["Files & Git Diff"])

@router.get("/tree")
async def get_workspace_file_tree(dir_path: str = "."):
    """Get the file tree structure of the workspace."""
    if not os.path.exists(dir_path):
        raise HTTPException(status_code=404, detail="Directory path not found")
    return GitService.list_file_tree(dir_path)

@router.get("/content")
async def get_file_content(path: str):
    """Retrieve content of a specific file."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File path not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"path": path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

@router.get("/git-diff")
async def get_overall_git_diff():
    """Retrieve current unified git diff for the workspace."""
    diff = GitService.get_git_diff()
    return {"diff": diff}

@router.get("/git-diff/file")
async def get_file_git_diff(path: str):
    """Retrieve git diff for a specific file."""
    diff = GitService.get_file_diff(path)
    return {"file_path": path, "diff": diff}

@router.get("/records/project/{project_id}", response_model=List[FileRecordResponse])
async def list_project_file_records(project_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve recorded file changes for a project from database."""
    stmt = select(FileRecord).where(FileRecord.project_id == project_id).order_by(FileRecord.timestamp.desc())
    res = await db.execute(stmt)
    return res.scalars().all()
