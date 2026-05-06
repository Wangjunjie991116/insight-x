"""Docker-based sandbox executor for safe code execution."""

import json
import tempfile
import time
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException
from docker.models.containers import Container

from src.config import get_settings
from src.models.result import ExecutionResult


class SandboxResult:
    """Result of sandbox execution."""

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
        """Convert to ExecutionResult model."""
        return ExecutionResult(
            success=self.success,
            output=self.output,
            logs=self.logs,
            error=self.error,
            duration_ms=self.duration_ms,
        )


class SandboxExecutor:
    """Execute Python code in Docker sandbox."""

    def __init__(self) -> None:
        """Initialize sandbox executor."""
        self._settings = get_settings()
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
        """Execute Python code in sandbox."""
        start_time = time.time()

        # Create temporary directory for code
        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "analysis.py"
            output_file = Path(tmpdir) / "output.json"

            # Prepare code with output capture
            full_code = self._prepare_code(code, db_config)
            code_file.write_text(full_code)

            # Run container
            try:
                container = self._run_container(tmpdir, timeout)
                logs = container.logs().decode("utf-8")

                # Get output
                output = self._get_output(container, output_file, tmpdir)

                # Cleanup
                container.remove()

                duration_ms = int((time.time() - start_time) * 1000)

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

    def _prepare_code(self, code: str, db_config: dict[str, Any] | None) -> str:
        """Prepare code with output capture."""
        db_config_json = json.dumps(db_config) if db_config else "{}"

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
    with open("/tmp/output.json", "w") as f:
        json.dump(output, f, default=str)
except Exception as e:
    with open("/tmp/output.json", "w") as f:
        json.dump({{"error": str(e)}}, f)
'''

    def _run_container(self, tmpdir: str, timeout: int | None) -> Container:
        """Run Docker container."""
        timeout = timeout or self._settings.sandbox_timeout

        return self._client.containers.run(
            self._settings.sandbox_image,
            command=f"python /tmp/analysis.py",
            volumes={
                tmpdir: {"bind": "/tmp", "mode": "rw"},
            },
            environment={
                "PYTHONUNBUFFERED": "1",
            },
            mem_limit=self._settings.sandbox_memory_limit,
            cpu_quota=self._settings.sandbox_cpu_quota,
            network_mode="none",
            detach=True,
        )

    def _get_output(
        self,
        container: Container,
        output_file: Path,
        tmpdir: str,
    ) -> dict[str, Any]:
        """Get output from container."""
        container.wait(timeout=self._settings.sandbox_timeout)

        output_path = Path(tmpdir) / "output.json"
        if output_path.exists():
            return json.loads(output_path.read_text())

        return {"status": "no_output"}
