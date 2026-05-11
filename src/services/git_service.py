"""Git 仓库服务：克隆仓库、提取文件树、识别技术栈。"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

from src.models.code_analysis import CodeRepository, FileNode

# 常见源码文件后缀，用于过滤和识别技术栈
_SOURCE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "react",
    ".tsx": "react",
    ".vue": "vue",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".rs": "rust",
}

_MAX_FILE_SIZE = 1024 * 1024  # 1MB，避免读取大文件
_MAX_FILES = 200  # 单次最多读取 200 个文件，控制 Token 消耗


class GitService:
    """基于系统 git 命令的异步仓库操作。"""

    async def clone_and_snapshot(
        self,
        repo_url: str,
        branch: str = "main",
        depth: int = 1,
    ) -> CodeRepository:
        """克隆仓库到临时目录，提取文件树并返回 CodeRepository。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            await self._clone(repo_url, branch, tmpdir, depth)
            commit_hash = await self._get_commit_hash(tmpdir)
            files = await self._extract_files(tmpdir)
            tech_stack = self._detect_tech_stack(files)

            return CodeRepository(
                repo_url=repo_url,
                branch=branch,
                commit_hash=commit_hash,
                files=files,
                tech_stack=tech_stack,
            )

    async def _clone(self, repo_url: str, branch: str, dest: str, depth: int) -> None:
        """异步执行 git clone。"""
        cmd = [
            "git",
            "clone",
            "--depth",
            str(depth),
            "--branch",
            branch,
            "--single-branch",
            repo_url,
            dest,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"git clone failed: {stderr.decode().strip() or stdout.decode().strip()}"
            )

    async def _get_commit_hash(self, repo_dir: str) -> str:
        """获取当前 HEAD commit hash。"""
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", repo_dir, "rev-parse", "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip() if proc.returncode == 0 else ""

    async def _extract_files(self, repo_dir: str) -> list[FileNode]:
        """遍历仓库目录，读取源码文件内容。"""
        repo_path = Path(repo_dir)
        files: list[FileNode] = []
        count = 0

        for item in repo_path.rglob("*"):
            # 跳过 .git 和 node_modules 等
            if any(part.startswith(".") or part in {"node_modules", "vendor", "__pycache__"} for part in item.relative_to(repo_path).parts):
                continue

            rel_path = str(item.relative_to(repo_path))

            if item.is_dir():
                files.append(FileNode(path=rel_path, is_directory=True))
                continue

            # 只读取源码文件，且控制数量
            if item.suffix.lower() not in _SOURCE_EXTENSIONS:
                continue
            if count >= _MAX_FILES:
                break
            if item.stat().st_size > _MAX_FILE_SIZE:
                continue

            try:
                content = item.read_text(encoding="utf-8", errors="ignore")
                files.append(FileNode(path=rel_path, content=content))
                count += 1
            except Exception:
                continue

        return files

    def _detect_tech_stack(self, files: list[FileNode]) -> list[str]:
        """基于文件后缀和关键配置文件识别技术栈。"""
        techs: set[str] = set()
        has_react = False
        has_vue = False
        has_next = False

        for f in files:
            ext = Path(f.path).suffix.lower()
            if ext in _SOURCE_EXTENSIONS:
                techs.add(_SOURCE_EXTENSIONS[ext])
            if ext == ".jsx" or ext == ".tsx":
                has_react = True
            if ext == ".vue":
                has_vue = True
            # 关键配置文件
            if f.path.endswith("next.config.js") or f.path.endswith("next.config.ts"):
                has_next = True
            if f.path.endswith("package.json") and not f.is_directory:
                if "next" in f.content:
                    has_next = True
                if "react" in f.content:
                    has_react = True
                if "vue" in f.content:
                    has_vue = True

        if has_next:
            techs.add("nextjs")
        elif has_react:
            techs.add("react")
        if has_vue:
            techs.add("vue")

        return sorted(techs)
