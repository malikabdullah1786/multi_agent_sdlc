import os
from pathlib import Path
from typing import Iterable, Optional, Sequence

_DEFAULT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".css", ".json", ".md", ".html",
    ".yml", ".yaml", ".toml", ".prisma",
}
_IGNORED_DIRS = {"node_modules", ".git", ".next", "dist", "build", "__pycache__", ".venv"}
_ROOT_DIR = Path(__file__).resolve().parents[3]


def build_codebase_context(
    subdir: Optional[str] = None,
    allowed_extensions: Optional[Iterable[str]] = None,
    preferred_keywords: Sequence[str] = (),
    max_total_chars: Optional[int] = None,
    max_file_chars: int = 5000,
    empty_message: str = "No files generated yet.",
) -> str:
    """
    Builds a provider-aware, budget-capped codebase summary:
    1. Compact file tree of all matching files under output/ (or output/<subdir>).
    2. File contents prioritized by preferred_keywords up to max_total_chars.
    """
    base_dir = _ROOT_DIR / "output"
    if subdir:
        base_dir = base_dir / subdir
    if not base_dir.exists():
        return empty_message

    exts = set(allowed_extensions) if allowed_extensions else _DEFAULT_EXTENSIONS
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    if max_total_chars is None:
        max_total_chars = 12000 if provider == "ollama" else 24000

    candidates: list[Path] = []
    for path in sorted(base_dir.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix in exts:
            candidates.append(path)

    if not candidates:
        return empty_message

    # Prioritize files matching preferred_keywords first, keeping relative order
    lowered_kw = [k.lower() for k in preferred_keywords if k]
    if lowered_kw:
        candidates.sort(
            key=lambda p: (
                0 if any(kw in str(p).lower() for kw in lowered_kw) else 1,
                str(p),
            )
        )

    tree_lines = ["### File Tree"]
    for p in candidates:
        rel = p.relative_to(_ROOT_DIR)
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        tree_lines.append(f"- {rel} ({size} bytes)")
    tree_section = "\n".join(tree_lines)

    code_blocks: list[str] = []
    omitted_files: list[str] = []
    current_chars = len(tree_section)

    for path in candidates:
        rel_path = path.relative_to(_ROOT_DIR)
        if current_chars >= max_total_chars:
            omitted_files.append(str(rel_path))
            continue
        try:
            content = path.read_text(encoding="utf-8")
            if len(content) > max_file_chars:
                content = content[:max_file_chars] + "\n... [TRUNCATED] ..."
            block = f"File: {rel_path}\n```\n{content}\n```"
            code_blocks.append(block)
            current_chars += len(block)
        except Exception as e:
            code_blocks.append(f"File: {rel_path} (Error: {e})")

    parts = [tree_section] + code_blocks
    if omitted_files:
        parts.append(
            "### Omitted files (use read_file_range / semantic_code_search to inspect):\n"
            + "\n".join(f"- {f}" for f in omitted_files)
        )
    return "\n\n".join(parts)
