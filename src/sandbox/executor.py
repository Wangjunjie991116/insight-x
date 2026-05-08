"""Docker 或本地子进程沙箱：包裹用户生成代码、捕获 JSON 输出并映射为 ExecutionResult。"""

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.models.result import ExecutionResult

# Optional Docker import
try:
    import docker
    from docker.errors import DockerException
    from docker.models.containers import Container

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False


class SandboxResult:
    """沙箱执行的原始产物：成功标志、解析后的 output dict、合并日志与耗时。"""

    def __init__(
        self,
        success: bool,
        output: dict[str, Any],
        logs: str,
        error: str | None = None,
        duration_ms: int = 0,
    ) -> None:
        self.success = success
        self.output = output
        self.logs = logs
        self.error = error
        self.duration_ms = duration_ms

    def to_execution_result(self) -> ExecutionResult:
        """转换为 API / Agent 层使用的 Pydantic 模型。"""
        return ExecutionResult(
            success=self.success,
            output=self.output,
            logs=self.logs,
            error=self.error,
            duration_ms=self.duration_ms,
        )


class SandboxExecutor:
    """根据 sandbox_mode 在 Docker（加固参数）或本机子进程中执行 analysis.py。"""

    def __init__(self) -> None:
        """docker 模式下懒连接 Docker daemon；失败直接抛错以便尽早暴露环境缺失。"""
        self._settings = get_settings()
        self._client = None

        if self._settings.sandbox_mode == "docker":
            if not DOCKER_AVAILABLE:
                raise RuntimeError("Docker mode requested but docker package not installed")
            try:
                self._client = docker.from_env()
            except DockerException as e:
                raise RuntimeError(f"Failed to connect to Docker: {e}") from e

    def execute(
        self,
        code: str,
        db_config: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> SandboxResult:
        """对外唯一入口：自动分流本地 / Docker。"""
        if self._settings.sandbox_mode == "local" or self._client is None:
            return self._execute_local(code, db_config, timeout)
        return self._execute_docker(code, db_config, timeout)

    def _execute_local(
        self,
        code: str,
        db_config: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> SandboxResult:
        """开发便利路径：与当前 Python 解释器同进程树，安全性低于 Docker。"""
        start_time = time.time()

        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "analysis.py"
            output_file = Path(tmpdir) / "output.json"

            full_code = self._prepare_code(code, db_config, output_file)
            code_file.write_text(full_code)

            try:
                import sys

                result = subprocess.run(
                    [sys.executable, str(code_file)],
                    capture_output=True,
                    text=True,
                    timeout=timeout or self._settings.sandbox_timeout,
                    cwd=tmpdir,
                )

                duration_ms = int((time.time() - start_time) * 1000)
                logs = result.stdout + result.stderr

                # 子进程 stdout/stderr 合并记入日志；结构化结果来自落地 JSON
                output = self._read_output(output_file)

                if result.returncode != 0:
                    return SandboxResult(
                        success=False,
                        output=output,
                        logs=logs,
                        error=f"Execution failed with exit code {result.returncode}",
                        duration_ms=duration_ms,
                    )

                return SandboxResult(
                    success=True,
                    output=output,
                    logs=logs,
                    duration_ms=duration_ms,
                )

            except subprocess.TimeoutExpired:
                duration_ms = int((time.time() - start_time) * 1000)
                return SandboxResult(
                    success=False,
                    output={},
                    logs="",
                    error="Execution timed out",
                    duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                return SandboxResult(
                    success=False,
                    output={},
                    logs="",
                    error=str(e),
                    duration_ms=duration_ms,
                )

    def _execute_docker(
        self,
        code: str,
        db_config: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> SandboxResult:
        """Docker 路径：只读挂载脚本、禁网、裁剪特权；日志从容器的 logs() 读取。"""
        start_time = time.time()
        container = None

        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "analysis.py"
            output_file = Path(tmpdir) / "output.json"

            full_code = self._prepare_code(code, db_config)
            code_file.write_text(full_code)

            try:
                container = self._run_container(code_file, timeout)
                result = container.wait(timeout=self._settings.sandbox_timeout)
                exit_code = result.get("StatusCode", 0)
                logs = container.logs().decode("utf-8")
                output = self._get_output(output_file)

                duration_ms = int((time.time() - start_time) * 1000)

                if exit_code != 0:
                    return SandboxResult(
                        success=False,
                        output=output,
                        logs=logs,
                        error=f"Execution failed with exit code {exit_code}",
                        duration_ms=duration_ms,
                    )

                return SandboxResult(
                    success=True,
                    output=output,
                    logs=logs,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                return SandboxResult(
                    success=False,
                    output={},
                    logs="",
                    error=str(e),
                    duration_ms=duration_ms,
                )
            finally:
                if container:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass

    def _prepare_code(
        self, code: str, db_config: dict[str, Any] | None, output_file: Path | None = None
    ) -> str:
        """在用户代码外包一层 DB_CONFIG 注入与 result→JSON 落盘，便于宿主读取。"""
        db_config_json = json.dumps(db_config) if db_config else "{}"
        output_path = str(output_file) if output_file else "/tmp/output.json"

        return f'''
import json
import sys

# Database config
DB_CONFIG = {db_config_json}

# User code
{code}

# Output capture
try:
    if 'result' in locals():
        output = result
    else:
        output = {{"status": "completed"}}
    with open("{output_path}", "w") as f:
        json.dump(output, f, default=str)
except Exception as e:
    with open("{output_path}", "w") as f:
        json.dump({{"error": str(e)}}, f)
'''

    def _run_container(self, code_file: Path, timeout: int | None) -> "Container":
        """创建一次性容器：resource/capability/network 均收紧；detach 便于 wait + 清理。"""
        timeout = timeout or self._settings.sandbox_timeout
        if self._client is None:
            raise RuntimeError("Docker client not initialized")
        return self._client.containers.run(
            self._settings.sandbox_image,
            command="python /tmp/analysis.py",
            volumes={
                str(code_file): {"bind": "/tmp/analysis.py", "mode": "ro"},
            },
            environment={
                "PYTHONUNBUFFERED": "1",
            },
            mem_limit=self._settings.sandbox_memory_limit,
            cpu_quota=self._settings.sandbox_cpu_quota,
            network_mode="none",
            security_opt=["no_new_privileges:true"],
            cap_drop=["ALL"],
            read_only=True,
            detach=True,
        )

    def _get_output(self, output_file: Path) -> dict[str, Any]:
        """Docker 结束后读宿主临时目录中的 output（与本地模式路径约定一致）。"""
        if output_file.exists():
            try:
                content = output_file.read_text()
                if content.strip():
                    data: dict[str, Any] = json.loads(content)
                    return data
            except json.JSONDecodeError as e:
                return {"error": f"JSON decode error: {e}", "raw_output": content}
            except Exception as e:
                return {"error": f"Failed to read output: {e}"}

        return {"status": "no_output"}

    def _read_output(self, output_file: Path) -> dict[str, Any]:
        """本地子进程写回访目录下的 output.json。"""
        if output_file.exists():
            try:
                content = output_file.read_text()
                if content.strip():
                    data: dict[str, Any] = json.loads(content)
                    return data
            except json.JSONDecodeError as e:
                return {"error": f"JSON decode error: {e}", "raw_output": content}
            except Exception as e:
                return {"error": f"Failed to read output: {e}"}

        return {"status": "no_output"}
