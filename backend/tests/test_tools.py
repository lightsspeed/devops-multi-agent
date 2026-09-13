import subprocess
from unittest.mock import MagicMock, patch

import pytest

from devops_agents.tools.kubernetes_tools import (
    kubectl_describe_pod,
    kubectl_get_events,
    kubectl_get_logs,
    kubectl_get_pods,
)
from devops_agents.tools.aws_tools import (
    aws_describe_instances,
    aws_get_cloudwatch_alarms,
    aws_list_s3_buckets,
)
from devops_agents.tools.linux_tools import (
    linux_check_logs,
    linux_check_process,
    linux_system_status,
)


# --- Kubernetes Tools Tests ---

@patch("subprocess.run")
def test_kubectl_get_pods_success(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["kubectl", "get", "pods"], returncode=0, stdout="payment-api-123   1/1   Running   0   5m"
    )
    res = kubectl_get_pods.invoke({"namespace": "default"})
    assert "payment-api-123" in res


def test_kubectl_get_pods_invalid_namespace():
    res = kubectl_get_pods.invoke({"namespace": "invalid;namespace"})
    assert "Error: Invalid namespace format" in res


@patch("subprocess.run", side_effect=FileNotFoundError())
def test_kubectl_get_pods_missing_binary(mock_run):
    res = kubectl_get_pods.invoke({"namespace": "default"})
    assert "executable not found" in res


@patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="kubectl", timeout=15))
def test_kubectl_get_pods_timeout(mock_run):
    res = kubectl_get_pods.invoke({"namespace": "default"})
    assert "timed out" in res


@patch("subprocess.run")
def test_kubectl_describe_pod_success(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["kubectl", "describe", "pod"], returncode=0, stdout="Name: payment-api\nStatus: Running"
    )
    res = kubectl_describe_pod.invoke({"pod_name": "payment-api", "namespace": "default"})
    assert "Name: payment-api" in res


def test_kubectl_describe_pod_invalid_name():
    res = kubectl_describe_pod.invoke({"pod_name": "pod;rm -rf", "namespace": "default"})
    assert "Error: Invalid pod name format" in res


@patch("subprocess.run")
def test_kubectl_get_events_success(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["kubectl", "get", "events"], returncode=0, stdout="Started container payment-api"
    )
    res = kubectl_get_events.invoke({"namespace": "default"})
    assert "Started container" in res


@patch("subprocess.run")
def test_kubectl_get_logs_success(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["kubectl", "logs"], returncode=0, stdout="Application started listening on :8080"
    )
    res = kubectl_get_logs.invoke({"pod_name": "payment-api", "namespace": "default", "previous": True})
    assert "listening on :8080" in res


# --- AWS Tools Tests ---

@patch("devops_agents.tools.aws_tools.HAS_BOTO3", True)
@patch("devops_agents.tools.aws_tools.boto3", create=True)
def test_aws_describe_instances_success(mock_boto3):
    mock_client = MagicMock()
    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-1234567890abcdef0",
                        "State": {"Name": "running"},
                        "InstanceType": "t3.medium",
                        "PrivateIpAddress": "10.0.1.50",
                    }
                ]
            }
        ]
    }
    mock_boto3.client.return_value = mock_client

    res = aws_describe_instances.invoke({"region": "us-east-1"})
    assert "i-1234567890abcdef0" in res
    assert "running" in res


@patch("devops_agents.tools.aws_tools.HAS_BOTO3", True)
@patch("devops_agents.tools.aws_tools.boto3", create=True)
def test_aws_list_s3_buckets_success(mock_boto3):
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {
        "Buckets": [{"Name": "my-devops-logs-bucket", "CreationDate": "2026-01-01"}]
    }
    mock_boto3.client.return_value = mock_client

    res = aws_list_s3_buckets.invoke({})
    assert "my-devops-logs-bucket" in res


@patch("devops_agents.tools.aws_tools.HAS_BOTO3", True)
@patch("devops_agents.tools.aws_tools.boto3", create=True)
def test_aws_get_cloudwatch_alarms_success(mock_boto3):
    mock_client = MagicMock()
    mock_client.describe_alarms.return_value = {
        "MetricAlarms": [
            {
                "AlarmName": "HighCPUUtilization",
                "StateValue": "ALARM",
                "StateReason": "CPU > 90%",
            }
        ]
    }
    mock_boto3.client.return_value = mock_client

    res = aws_get_cloudwatch_alarms.invoke({"region": "us-east-1"})
    assert "HighCPUUtilization" in res
    assert "ALARM" in res



# --- Linux Tools Tests ---

@patch("subprocess.run")
def test_linux_system_status_success(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["free", "-m"], returncode=0, stdout="Mem: 16000 4000 12000"
    )
    res = linux_system_status.invoke({})
    assert "Mem:" in res or "Disk" in res or "System Info" in res


def test_linux_check_process_invalid_name():
    res = linux_check_process.invoke({"process_name": "nginx; bad!name"})
    assert "Error: Invalid process name format" in res


@patch("subprocess.run")
def test_linux_check_process_success(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["ps", "aux"], returncode=0, stdout="root 100 0.0 0.1 /usr/sbin/nginx"
    )
    res = linux_check_process.invoke({"process_name": "nginx"})
    assert "nginx" in res


def test_linux_check_logs_invalid_service():
    res = linux_check_logs.invoke({"service_name": "nginx; bad!service"})
    assert "Error: Invalid service name format" in res


@patch("subprocess.run")
def test_linux_check_logs_success(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["journalctl"], returncode=0, stdout="Started Nginx Web Server"
    )
    res = linux_check_logs.invoke({"service_name": "nginx", "lines": 20})
    assert "Started Nginx" in res


# --- Read-Only Tool Enforcement Policy Tests ---

@pytest.mark.parametrize("write_verb", ["delete", "patch", "scale", "rollout", "set", "apply", "restart", "exec"])
def test_kubectl_read_only_safety_blocks_write_verbs(write_verb):
    res = kubectl_get_pods.invoke({"namespace": f"default-{write_verb}"})
    assert "Read-only safety policy violation" in res
    assert write_verb in res


@pytest.mark.parametrize("write_verb", ["terminate", "delete", "stop", "start", "create"])
def test_aws_read_only_safety_blocks_write_verbs(write_verb):
    res = aws_describe_instances.invoke({"region": f"us-east-{write_verb}"})
    assert "Read-only safety policy violation" in res
    assert write_verb in res


@pytest.mark.parametrize("write_verb", ["kill", "rm", "reboot", "shutdown", "restart", "systemctl"])
def test_linux_read_only_safety_blocks_write_verbs(write_verb):
    res = linux_check_logs.invoke({"service_name": f"nginx-{write_verb}"})
    assert "Read-only safety policy violation" in res
    assert write_verb in res

