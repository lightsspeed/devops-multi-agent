import os
import platform
import re
import subprocess
from typing import Optional
from langchain_core.tools import tool



BLOCKED_WRITE_VERBS = {
    "kill", "rm", "reboot", "shutdown", "restart", "stop", "start",
    "systemctl", "chmod", "chown", "touch", "dd", "mkfs", "apply", "delete",
    "create", "edit", "patch", "replace", "scale", "rollout", "set",
    "bash", "sh", "cmd", "powershell", "eval"
}


def _validate_name(name: str) -> bool:
    """Validate process or service name against safe regex."""
    return bool(re.match(r"^[a-zA-Z0-9_\.-]+$", name))


def _check_read_only_safety(*inputs: str) -> Optional[str]:
    """Check if any input contains blocked write verbs."""
    for item in inputs:
        if not item:
            continue
        tokens = re.findall(r"[a-zA-Z]+", str(item).lower())
        for token in tokens:
            if token in BLOCKED_WRITE_VERBS:
                return f"Error: Read-only safety policy violation. Write operation '{token}' is blocked."
    return None



@tool
def linux_system_status() -> str:
    """Get system resource utilization including memory (free), disk space (df), and uptime (read-only)."""
    output_parts = []
    is_windows = platform.system() == "Windows"

    # Memory check
    try:
        if is_windows:
            mem_res = subprocess.run(["systeminfo"], capture_output=True, text=True, timeout=10)
            output_parts.append("--- System Info ---\n" + mem_res.stdout[:500])
        else:
            free_res = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=10, check=True)
            output_parts.append("--- Memory Usage (free -m) ---\n" + free_res.stdout.strip())
    except Exception as exc:
        output_parts.append(f"Memory check unavailable: {str(exc)}")

    # Disk check
    try:
        if is_windows:
            df_res = subprocess.run(["wmic", "logicaldisk", "get", "size,freespace,caption"], capture_output=True, text=True, timeout=10)
            output_parts.append("--- Disk Usage ---\n" + df_res.stdout.strip())
        else:
            df_res = subprocess.run(["df", "-h"], capture_output=True, text=True, timeout=10, check=True)
            output_parts.append("--- Disk Usage (df -h) ---\n" + df_res.stdout.strip())
    except Exception as exc:
        output_parts.append(f"Disk check unavailable: {str(exc)}")

    # Uptime check
    try:
        if not is_windows:
            uptime_res = subprocess.run(["uptime"], capture_output=True, text=True, timeout=10, check=True)
            output_parts.append("--- System Uptime ---\n" + uptime_res.stdout.strip())
    except Exception:
        pass

    return "\n\n".join(output_parts) if output_parts else "Unable to retrieve system status."


@tool
def linux_check_process(process_name: str) -> str:
    """Check if a specific process is running using ps/tasklist (read-only)."""
    safety_err = _check_read_only_safety(process_name)
    if safety_err:
        return safety_err
    if not _validate_name(process_name):
        return f"Error: Invalid process name format '{process_name}'."

    is_windows = platform.system() == "Windows"

    try:
        if is_windows:
            res = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {process_name}*"], capture_output=True, text=True, timeout=10, check=True)
            return res.stdout.strip()
        else:
            res = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10, check=True)
            matching = [line for line in res.stdout.splitlines() if process_name in line]
            if not matching:
                return f"No process matching '{process_name}' found."
            return f"Matching processes for '{process_name}':\n" + "\n".join(matching[:20])
    except FileNotFoundError:
        return "Error: Process status command executable not found."
    except subprocess.TimeoutExpired:
        return f"Error: Process check for '{process_name}' timed out."
    except Exception as exc:
        return f"Error checking process '{process_name}': {str(exc)}"


@tool
def linux_check_logs(service_name: str, lines: int = 50) -> str:
    """Get systemd service logs using journalctl -u <service_name> -n <lines> (read-only)."""
    safety_err = _check_read_only_safety(service_name)
    if safety_err:
        return safety_err
    if not _validate_name(service_name):
        return f"Error: Invalid service name format '{service_name}'."


    lines = min(max(lines, 1), 200)

    try:
        res = subprocess.run(
            ["journalctl", "-u", service_name, "-n", str(lines), "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return res.stdout if res.stdout.strip() else f"No logs found for service '{service_name}'."
    except FileNotFoundError:
        return "Error: 'journalctl' executable not found (system is not using systemd or on non-Linux OS)."
    except subprocess.TimeoutExpired:
        return f"Error: Log check for service '{service_name}' timed out."
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        return f"journalctl failed for service '{service_name}': {stderr}"
