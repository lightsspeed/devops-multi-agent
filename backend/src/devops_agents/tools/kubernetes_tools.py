import re
import subprocess
from typing import Optional
from langchain_core.tools import tool


BLOCKED_WRITE_VERBS = {
    "apply", "delete", "create", "edit", "patch", "replace", "scale", "rollout",
    "set", "label", "annotate", "exec", "cp", "drain", "cordon", "uncordon",
    "kill", "reboot", "shutdown", "restart", "stop", "start", "terminate", "rollback",
    "put", "update", "modify", "attach", "detach", "remove", "drop", "truncate",
    "bash", "sh", "cmd", "powershell", "eval"
}


def _validate_name(name: str) -> bool:
    """Validate resource name to allow only valid Kubernetes identifiers."""
    return bool(re.match(r"^[a-zA-Z0-9\.-]+$", name))


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
def kubectl_get_pods(namespace: str = "default") -> str:
    """Get list of Kubernetes pods in a namespace using kubectl get pods."""
    safety_err = _check_read_only_safety(namespace)
    if safety_err:
        return safety_err
    if not _validate_name(namespace):
        return f"Error: Invalid namespace format '{namespace}'."

    try:
        res = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return res.stdout if res.stdout.strip() else "No pods found in namespace."
    except FileNotFoundError:
        return "Error: 'kubectl' executable not found in system PATH. Please install kubectl and configure kubeconfig."
    except subprocess.TimeoutExpired:
        return "Error: 'kubectl get pods' command timed out after 15 seconds."
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        return f"kubectl get pods failed (exit code {exc.returncode}): {stderr}"


@tool
def kubectl_describe_pod(pod_name: str, namespace: str = "default") -> str:
    """Describe a specific Kubernetes pod using kubectl describe pod <pod_name>."""
    safety_err = _check_read_only_safety(pod_name, namespace)
    if safety_err:
        return safety_err
    if not _validate_name(pod_name):
        return f"Error: Invalid pod name format '{pod_name}'."
    if not _validate_name(namespace):
        return f"Error: Invalid namespace format '{namespace}'."

    try:
        res = subprocess.run(
            ["kubectl", "describe", "pod", pod_name, "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return res.stdout if res.stdout.strip() else f"No details returned for pod '{pod_name}'."
    except FileNotFoundError:
        return "Error: 'kubectl' executable not found in system PATH. Please install kubectl and configure kubeconfig."
    except subprocess.TimeoutExpired:
        return f"Error: 'kubectl describe pod {pod_name}' command timed out after 15 seconds."
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        return f"kubectl describe pod failed (exit code {exc.returncode}): {stderr}"


@tool
def kubectl_get_events(namespace: str = "default") -> str:
    """Get recent events in a Kubernetes namespace using kubectl get events."""
    safety_err = _check_read_only_safety(namespace)
    if safety_err:
        return safety_err
    if not _validate_name(namespace):
        return f"Error: Invalid namespace format '{namespace}'."

    try:
        res = subprocess.run(
            ["kubectl", "get", "events", "-n", namespace, "--sort-by=.metadata.creationTimestamp"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return res.stdout if res.stdout.strip() else "No events found in namespace."
    except FileNotFoundError:
        return "Error: 'kubectl' executable not found in system PATH. Please install kubectl and configure kubeconfig."
    except subprocess.TimeoutExpired:
        return "Error: 'kubectl get events' command timed out after 15 seconds."
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        return f"kubectl get events failed (exit code {exc.returncode}): {stderr}"


@tool
def kubectl_get_logs(pod_name: str, namespace: str = "default", previous: bool = False) -> str:
    """Get logs for a Kubernetes pod using kubectl logs <pod_name> [--previous]."""
    safety_err = _check_read_only_safety(pod_name, namespace)
    if safety_err:
        return safety_err
    if not _validate_name(pod_name):
        return f"Error: Invalid pod name format '{pod_name}'."
    if not _validate_name(namespace):
        return f"Error: Invalid namespace format '{namespace}'."


    cmd = ["kubectl", "logs", pod_name, "-n", namespace]
    if previous:
        cmd.append("--previous")

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return res.stdout if res.stdout.strip() else f"No logs available for pod '{pod_name}'."
    except FileNotFoundError:
        return "Error: 'kubectl' executable not found in system PATH. Please install kubectl and configure kubeconfig."
    except subprocess.TimeoutExpired:
        return f"Error: 'kubectl logs {pod_name}' command timed out after 15 seconds."
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        return f"kubectl logs failed (exit code {exc.returncode}): {stderr}"


@tool
def kubectl_get_deployment(deployment_name: str, namespace: str = "default") -> str:
    """Get the status of a specific Kubernetes Deployment using kubectl get deployment <name> -o wide.
    
    Returns DESIRED, READY, UP-TO-DATE, and AVAILABLE replica counts plus
    conditions, which allow correct determination of whether the Deployment
    itself is unavailable (not merely whether an individual pod is unhealthy).
    """
    safety_err = _check_read_only_safety(deployment_name, namespace)
    if safety_err:
        return safety_err
    if not _validate_name(deployment_name):
        return f"Error: Invalid deployment name format '{deployment_name}'."
    if not _validate_name(namespace):
        return f"Error: Invalid namespace format '{namespace}'."

    try:
        res = subprocess.run(
            [
                "kubectl", "get", "deployment", deployment_name,
                "-n", namespace,
                "-o", "wide",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        output = res.stdout.strip()
        if not output:
            return f"No deployment named '{deployment_name}' found in namespace '{namespace}'."
        return output
    except FileNotFoundError:
        return "Error: 'kubectl' executable not found in system PATH. Please install kubectl and configure kubeconfig."
    except subprocess.TimeoutExpired:
        return f"Error: 'kubectl get deployment {deployment_name}' command timed out after 15 seconds."
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        return f"kubectl get deployment failed (exit code {exc.returncode}): {stderr}"

