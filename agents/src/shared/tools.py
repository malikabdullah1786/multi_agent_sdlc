"""
Shared Agent Tools — Generic terminal execution tool.
"""
import subprocess
from pathlib import Path
from langchain_core.tools import tool

_ROOT_DIR = Path(__file__).resolve().parents[3]
_OUTPUT_DIR = _ROOT_DIR / "output"

@tool
def run_terminal_command(command: str) -> str:
    """
    Executes any generic shell / terminal command inside the project's output directory.
    Args:
        command: The exact shell command line string to execute (e.g. 'npm install axios', 'python script.py').
    """
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Non-blocking non-interactive auto-fix for npm install
    if command.startswith("npm install") and "--legacy-peer-deps" not in command:
        command += " --legacy-peer-deps"
        
    try:
        res = subprocess.run(
            command,
            shell=True,
            cwd=str(_OUTPUT_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180
        )
        stdout = res.stdout.strip()
        stderr = res.stderr.strip()
        
        try:
            from backend.telemetry import broadcast_tool_call
            broadcast_tool_call(
                "run_terminal_command",
                command,
                event_type="TERMINAL_COMMAND",
                payload_extra={
                    "command": command,
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": res.returncode
                }
            )
        except Exception:
            pass

        if res.returncode == 0:
            output = stdout or stderr or "Command completed with exit code 0."
            return f"COMMAND_SUCCESS ({command}):\n{output[:2000]}"
        else:
            output = stderr or stdout or "Command failed."
            return f"COMMAND_FAILED (exit code {res.returncode}):\n{output[:2000]}"
    except subprocess.TimeoutExpired:
        return f"COMMAND_TIMEOUT: Command '{command}' timed out after 180s."
    except Exception as e:
        return f"COMMAND_ERROR: {e}"
