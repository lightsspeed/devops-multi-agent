from devops_agents.tools.kubernetes_tools import (
    kubectl_describe_pod,
    kubectl_get_events,
    kubectl_get_logs,
    kubectl_get_pods,
    kubectl_get_deployment,
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

KUBERNETES_TOOLS = [
    kubectl_get_pods,
    kubectl_get_deployment,
    kubectl_describe_pod,
    kubectl_get_events,
    kubectl_get_logs,
]

AWS_TOOLS = [
    aws_describe_instances,
    aws_list_s3_buckets,
    aws_get_cloudwatch_alarms,
]

LINUX_TOOLS = [
    linux_system_status,
    linux_check_process,
    linux_check_logs,
]

__all__ = [
    "KUBERNETES_TOOLS",
    "AWS_TOOLS",
    "LINUX_TOOLS",
    "kubectl_get_pods",
    "kubectl_get_deployment",
    "kubectl_describe_pod",
    "kubectl_get_events",
    "kubectl_get_logs",
    "aws_describe_instances",
    "aws_list_s3_buckets",
    "aws_get_cloudwatch_alarms",
    "linux_system_status",
    "linux_check_process",
    "linux_check_logs",
]
