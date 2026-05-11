"""Agent 7：代码实现 Agent。

将 Agent 6-1 的代码优化建议与 Agent 6-2 的埋点策略转换为统一 diff 格式的 patch 文件。
"""

import difflib
import json
from typing import Any

from src.agents.base import BaseAgent
from src.llm.prompts import PromptTemplates
from src.models.code_analysis import (
    CodeChangeSuggestion,
    CodeImplementationOutput,
    CodeRepository,
    FileChange,
    TrackingEventDesign,
    TrackingStrategyReport,
)


class CodeImplementationInput:
    """Agent 7 的输入。"""

    def __init__(
        self,
        repo: CodeRepository,
        code_suggestions: list[CodeChangeSuggestion] | None = None,
        tracking_report: TrackingStrategyReport | None = None,
    ) -> None:
        self.repo = repo
        self.code_suggestions = code_suggestions or []
        self.tracking_report = tracking_report


class CodeImplementationAgent(BaseAgent[CodeImplementationInput, CodeImplementationOutput]):
    """流水线第 7 步：把分析结论翻译成可合并的代码修改（unified diff）。"""

    @property
    def name(self) -> str:
        return "CodeImplementationAgent"

    @property
    def description(self) -> str:
        return "Generates unified diff patches from optimization suggestions and tracking strategies"

    async def execute(self, input_data: CodeImplementationInput) -> CodeImplementationOutput:
        """分文件生成修改后的源码，再 diff 为 patch。"""
        self._log_execution("Generating code changes...")

        all_changes: list[FileChange] = []
        pr_parts: list[str] = []
        test_suggestions: list[str] = []

        # 处理 Agent 6-1 的代码优化建议
        if input_data.code_suggestions:
            self._log_execution(f"Processing {len(input_data.code_suggestions)} code optimization suggestions...")
            opt_changes, opt_pr, opt_tests = await self._apply_code_suggestions(
                input_data.repo, input_data.code_suggestions
            )
            all_changes.extend(opt_changes)
            pr_parts.append(opt_pr)
            test_suggestions.extend(opt_tests)

        # 处理 Agent 6-2 的埋点策略
        if input_data.tracking_report and input_data.tracking_report.new_events:
            self._log_execution(f"Processing {len(input_data.tracking_report.new_events)} tracking events...")
            track_changes, track_pr, track_tests = await self._apply_tracking_report(
                input_data.repo, input_data.tracking_report
            )
            all_changes.extend(track_changes)
            pr_parts.append(track_pr)
            test_suggestions.extend(track_tests)

        pr_description = "\n\n".join(pr_parts)
        self._log_execution(f"Generated {len(all_changes)} file changes")

        return CodeImplementationOutput(
            changes=all_changes,
            pr_description=pr_description,
            test_suggestions=test_suggestions,
        )

    async def _apply_code_suggestions(
        self,
        repo: CodeRepository,
        suggestions: list[CodeChangeSuggestion],
    ) -> tuple[list[FileChange], str, list[str]]:
        """按文件聚合优化建议，调用 LLM 生成修改后源码，再 diff。"""
        # 按文件路径分组
        by_file: dict[str, list[CodeChangeSuggestion]] = {}
        for s in suggestions:
            by_file.setdefault(s.file_path, []).append(s)

        changes: list[FileChange] = []
        pr_lines: list[str] = ["## 代码优化变更", ""]
        tests: list[str] = []

        for file_path, file_suggestions in by_file.items():
            file_node = repo.get_file(file_path)
            if not file_node:
                self._log_execution(f"File not found in repo: {file_path}")
                continue

            original = file_node.content
            suggestions_json = json.dumps(
                [s.model_dump() for s in file_suggestions],
                indent=2,
                ensure_ascii=False,
            )

            try:
                system_prompt, user_prompt = PromptTemplates.format_code_implementation(
                    original_code=original,
                    file_path=file_path,
                    suggestions=suggestions_json,
                    change_type="optimization",
                )
                modified = await self._call_llm(system_prompt, user_prompt)
                modified = self._extract_code(modified)

                diff = self._make_diff(original, modified, file_path)
                if diff:
                    changes.append(FileChange(file_path=file_path, diff=diff, change_type="modify"))
                    pr_lines.append(f"- `{file_path}`: {len(file_suggestions)} optimization(s)")
                    for s in file_suggestions:
                        pr_lines.append(f"  - {s.rationale}")
                        if s.target_metric:
                            tests.append(f"验证指标 {s.target_metric} 是否改善")
            except Exception as e:
                self._log_execution(f"Failed to apply suggestions to {file_path}: {e}")

        return changes, "\n".join(pr_lines), tests

    async def _apply_tracking_report(
        self,
        repo: CodeRepository,
        report: TrackingStrategyReport,
    ) -> tuple[list[FileChange], str, list[str]]:
        """按文件路径聚合埋点事件，调用 LLM 生成修改后源码，再 diff。"""
        # 按 code_location（文件路径）分组
        by_file: dict[str, list[TrackingEventDesign]] = {}
        for ev in report.new_events:
            # code_location 可能为 "src/pages/Checkout.tsx:78"，提取文件路径
            loc = ev.code_location.split(":")[0] if ev.code_location else ""
            if loc:
                by_file.setdefault(loc, []).append(ev)
            else:
                # 如果没有指定文件，尝试从事件名推断或留空
                by_file.setdefault("TRACKING_PLACEHOLDER", []).append(ev)

        changes: list[FileChange] = []
        pr_lines: list[str] = ["## 埋点事件变更", ""]
        tests: list[str] = []

        for file_path, events in by_file.items():
            if file_path == "TRACKING_PLACEHOLDER":
                # 没有明确文件位置的埋点，只记录说明，不生成 diff
                pr_lines.append("- 以下埋点未指定具体文件位置，需手动植入：")
                for ev in events:
                    pr_lines.append(f"  - `{ev.event_name}`: {ev.implementation_hint}")
                continue

            file_node = repo.get_file(file_path)
            if not file_node:
                self._log_execution(f"File not found in repo: {file_path}")
                continue

            original = file_node.content
            events_json = json.dumps(
                [e.model_dump() for e in events],
                indent=2,
                ensure_ascii=False,
            )

            try:
                system_prompt, user_prompt = PromptTemplates.format_code_implementation(
                    original_code=original,
                    file_path=file_path,
                    suggestions=events_json,
                    change_type="tracking",
                )
                modified = await self._call_llm(system_prompt, user_prompt)
                modified = self._extract_code(modified)

                diff = self._make_diff(original, modified, file_path)
                if diff:
                    changes.append(FileChange(file_path=file_path, diff=diff, change_type="modify"))
                    pr_lines.append(f"- `{file_path}`: added {len(events)} tracking event(s)")
                    for ev in events:
                        pr_lines.append(f"  - `{ev.event_name}`: {ev.business_hypothesis}")
                        tests.append(f"验证埋点 {ev.event_name} 是否正常上报")
            except Exception as e:
                self._log_execution(f"Failed to apply tracking to {file_path}: {e}")

        return changes, "\n".join(pr_lines), tests

    def _extract_code(self, response: str) -> str:
        """从 LLM 响应中提取纯代码内容，去掉 markdown 围栏。"""
        cleaned = response.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline + 1 :]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        return cleaned

    def _make_diff(self, original: str, modified: str, file_path: str) -> str:
        """使用 difflib 生成统一 diff 格式。"""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        # 确保每行以换行符结尾，difflib 行为更稳定
        if original_lines and not original_lines[-1].endswith("\n"):
            original_lines[-1] += "\n"
        if modified_lines and not modified_lines[-1].endswith("\n"):
            modified_lines[-1] += "\n"

        diff_lines = list(
            difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
            )
        )
        return "".join(diff_lines)
