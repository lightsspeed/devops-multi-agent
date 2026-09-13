import re
from typing import Optional
from langchain_core.tools import tool

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    HAS_BOTO3 = True
except (ImportError, ModuleNotFoundError):
    HAS_BOTO3 = False
    class BotoCoreError(Exception): pass
    class ClientError(Exception): pass
    class NoCredentialsError(Exception): pass


BLOCKED_WRITE_VERBS = {
    "create", "delete", "terminate", "stop", "start", "reboot", "update",
    "put", "modify", "attach", "detach", "remove", "drop", "truncate",
    "apply", "edit", "patch", "replace", "scale", "rollout", "set",
    "bash", "sh", "cmd", "powershell", "eval"
}


def _validate_name(name: str) -> bool:
    """Validate resource/region name against safe regex."""
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
def aws_describe_instances(region: str = "us-east-1") -> str:
    """Describe EC2 instances in an AWS region (read-only)."""
    safety_err = _check_read_only_safety(region)
    if safety_err:
        return safety_err
    if not _validate_name(region):
        return f"Error: Invalid region format '{region}'."

    if not HAS_BOTO3:
        return "Error: 'boto3' Python package is not installed. Run 'pip install boto3' to enable AWS tools."

    try:
        ec2 = boto3.client("ec2", region_name=region)
        response = ec2.describe_instances()

        instances_info = []
        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                inst_id = inst.get("InstanceId")
                state = inst.get("State", {}).get("Name")
                itype = inst.get("InstanceType")
                ip = inst.get("PrivateIpAddress", "N/A")
                instances_info.append(f"ID: {inst_id} | Type: {itype} | State: {state} | Private IP: {ip}")

        if not instances_info:
            return f"No EC2 instances found in region {region}."
        return f"EC2 Instances in {region}:\n" + "\n".join(instances_info)

    except NoCredentialsError:
        return "Error: AWS credentials not found. Please configure ~/.aws/credentials or environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)."
    except ClientError as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "Unknown")
        msg = getattr(exc, "response", {}).get("Error", {}).get("Message", str(exc))
        return f"AWS API Error ({code}): {msg}"
    except Exception as exc:
        return f"Error executing AWS describe_instances: {str(exc)}"


@tool
def aws_list_s3_buckets() -> str:
    """List S3 buckets in the AWS account (read-only)."""
    if not HAS_BOTO3:
        return "Error: 'boto3' Python package is not installed. Run 'pip install boto3' to enable AWS tools."

    try:
        s3 = boto3.client("s3")
        response = s3.list_buckets()

        buckets = response.get("Buckets", [])
        if not buckets:
            return "No S3 buckets found in account."

        bucket_names = [f"- {b.get('Name')} (Created: {b.get('CreationDate')})" for b in buckets]
        return "S3 Buckets:\n" + "\n".join(bucket_names)

    except NoCredentialsError:
        return "Error: AWS credentials not found. Please configure ~/.aws/credentials or environment variables."
    except ClientError as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "Unknown")
        msg = getattr(exc, "response", {}).get("Error", {}).get("Message", str(exc))
        return f"AWS API Error ({code}): {msg}"
    except Exception as exc:
        return f"Error executing AWS list_s3_buckets: {str(exc)}"


@tool
def aws_get_cloudwatch_alarms(region: str = "us-east-1") -> str:
    """Get CloudWatch alarms in an AWS region (read-only)."""
    safety_err = _check_read_only_safety(region)
    if safety_err:
        return safety_err
    if not _validate_name(region):
        return f"Error: Invalid region format '{region}'."

    if not HAS_BOTO3:
        return "Error: 'boto3' Python package is not installed. Run 'pip install boto3' to enable AWS tools."

    try:
        cw = boto3.client("cloudwatch", region_name=region)
        response = cw.describe_alarms()

        metric_alarms = response.get("MetricAlarms", [])
        if not metric_alarms:
            return f"No CloudWatch metric alarms found in region {region}."

        alarm_info = []
        for alarm in metric_alarms:
            name = alarm.get("AlarmName")
            state = alarm.get("StateValue")
            reason = alarm.get("StateReason", "")
            alarm_info.append(f"Alarm: {name} | State: {state} | Reason: {reason}")

        return f"CloudWatch Alarms in {region}:\n" + "\n".join(alarm_info)

    except NoCredentialsError:
        return "Error: AWS credentials not found. Please configure ~/.aws/credentials or environment variables."
    except ClientError as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "Unknown")
        msg = getattr(exc, "response", {}).get("Error", {}).get("Message", str(exc))
        return f"AWS API Error ({code}): {msg}"
    except Exception as exc:
        return f"Error executing AWS get_cloudwatch_alarms: {str(exc)}"

