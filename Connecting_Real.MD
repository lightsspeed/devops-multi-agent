Here is how you can connect your application to your **real Kubernetes cluster**, **AWS Account**, and **Linux Server**:

---

### 1. Connecting a Real Kubernetes Cluster

The Kubernetes agent executes standard `kubectl` commands. It uses whatever cluster is set as your **active context** in `kubeconfig`.

#### Steps:
1. **Ensure `kubectl` is installed on your system:**
   ```powershell
   kubectl version --client
   ```
   *(If not installed, run `winget install -e --id Kubernetes.kubectl` or install via Docker Desktop / Minikube).*

2. **Configure your cluster credentials (`kubeconfig`):**
   - **Managed EKS (AWS):**
     ```bash
     aws eks update-kubeconfig --region us-east-1 --name <your-cluster-name>
     ```
   - **Self-hosted / Cloud (GKE, AKS, DigitalOcean, etc.):**
     Copy your cluster `config` file to `C:\Users\<YourUsername>\.kube\config`.
   - **Local Cluster (Minikube / Kind / Docker Desktop):**
     ```bash
     minikube start   # or enable Kubernetes in Docker Desktop settings
     ```

3. **Verify Connection:**
   ```powershell
   kubectl get nodes
   kubectl get pods -n default
   ```
   *Once `kubectl get pods` returns output in your terminal, the Kubernetes Agent will automatically query your live cluster!*

---

### 2. Connecting a Real AWS Account

The AWS agent uses `boto3`, which follows the standard AWS credential chain.

#### Steps:
1. **Install `boto3` in your Python backend environment:**
   ```powershell
   python -m pip install boto3
   ```

2. **Configure AWS Credentials (Choose one option):**

   - **Option A (AWS CLI - Recommended):**
     Run `aws configure` in terminal and input your credentials:
     ```text
     AWS Access Key ID: AKIAXXXXXXXXXXXXXXXX
     AWS Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
     Default region name: us-east-1
     Default output format: json
     ```

   - **Option B (Environment Variables in PowerShell):**
     ```powershell
     $env:AWS_ACCESS_KEY_ID="AKIAXXXXXXXXXXXXXXXX"
     $env:AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
     $env:AWS_DEFAULT_REGION="us-east-1"
     ```

3. **Verify Connection:**
   ```powershell
   python -c "import boto3; print(boto3.client('sts').get_caller_identity())"
   ```
   *Once `get_caller_identity()` returns your IAM user/role ARN, the AWS Agent will automatically query your real EC2 instances, S3 buckets, and CloudWatch alarms!*

---

### 3. Connecting a Real Linux Server

Linux tools (`free -m`, `df -h`, `ps aux`, `journalctl`) execute read-only system commands.

#### Options:
- **Option A (WSL2 / Linux OS / Docker Container):**
  If running the backend inside Linux, WSL2, or a Linux Docker container, tools run directly against the local Linux OS host.
- **Option B (Remote Linux Server via SSH or AWS SSM):**
  If your Linux server is remote (e.g. an EC2 instance or remote server), we can add an SSH connector (`paramiko`) or AWS Systems Manager (`aws ssm send-command`) tool so the Linux Agent can run commands remotely over SSH or SSM!