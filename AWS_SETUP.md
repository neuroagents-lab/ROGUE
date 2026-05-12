# ☁ Configuration of AWS

We provide an AWS-based platform for large-scale parallel evaluation of ROGUE tasks. This file provides the documentation for setting up the AWS platform, including required security group ports, VPC setup, and AMI configuration.

The AWS cloud service architecture consists of a host machine that controls multiple virtual machines (each virtual machine serves as an environment, for which we provide AMI images) for testing and potential training purposes. To prevent security breaches, we need to properly configure security groups for both the host machine and virtual machines, as well as configure appropriate subnets.

### Prerequisites

Before starting, make sure you have:

1. An AWS account with permission to create EC2 instances, security groups, key pairs, and access keys.
2. Access to the AWS Console.
3. The AWS CLI installed on the host machine if you want to run the verification commands in this guide.

This guide uses environment variables for AWS credentials and configuration. You do not need to run `aws configure`.

For a first-time setup, use `us-east-1` for every AWS region field in the console, in environment variables, and in evaluation commands. The examples below assume the default AWS VPC network range `172.31.0.0/16`.

### Architecture Overview

- **Host Instance**: Central controller that stores code, configurations, and manages task execution
- **Client Instances**: Worker nodes automatically launched by the code to perform tasks in parallel

You manually create the host instance. You do not manually create the client instances. The code launches client instances using the subnet ID and client security group ID that you export below.

### Platform Deployment

#### Step 0: Choose the AWS Region

Use `us-east-1` unless you have a specific reason to use another supported region.

1. Sign in to the AWS Console.
2. In the top-right region selector, choose **US East (N. Virginia) us-east-1**.
3. Use the same region later for:
   - `AWS_REGION`
   - Evaluation command arguments such as `--region us-east-1`
   - The host EC2 instance
   - The client security group
   - The subnet used by `AWS_SUBNET_ID`

The AWS provider code currently defines supported AMIs in `desktop_env/providers/aws/manager.py`:

| Region | Screen Size | AMI ID |
|--------|-------------|--------|
| `us-east-1` | `1920x1080` | `ami-0d23263edb96951d8` |
| `ap-east-1` | `1920x1080` | `ami-06850864d18fad836` |

Make sure the AMI image you use is available in your AWS region and permissioned for your AWS account.

#### Step 1: Launch the Host Instance

The host instance is the machine where you run this repository and start evaluations.

1. Open the AWS Console.
2. Go to **EC2**.
3. In the left sidebar, click **Instances**.
4. Click **Launch instances**.
5. In **Name and tags**, set the instance name to something recognizable, such as `rogue-host`.
6. In **Application and OS Images (Amazon Machine Image)**, choose:
   - **Ubuntu Server 24.04 LTS (HVM), SSD Volume Type**
7. In **Instance type**, choose based on expected parallelism:
   - `t3.medium`: For < 5 parallel environments
   - `t3.large`: For < 15 parallel environments
   - `c4.8xlarge`: For 15+ parallel environments
8. In **Key pair (login)**:
   - Create a new key pair if you do not already have one.
   - Use `.pem` format.
   - Download the `.pem` file and save it somewhere you can find again, such as `~/Downloads/rogue-host-key.pem`.
9. In **Network settings**:
   - **VPC**: Use the default VPC. Note the VPC ID for later.
   - **Subnet**: Choose a subnet in the default VPC. Note the Subnet ID for later.
   - **Auto-assign public IP**: Enable.
   - **Security group**: Create a host security group, such as `rogue-host-sg`.
10. For the host security group, allow inbound access for:
    - `SSH` / `TCP` / port `22` / source `0.0.0.0/0` / SSH access to the host
    - `Custom TCP` / `TCP` / port `8080` / source `0.0.0.0/0` / monitor service, if used
11. In **Configure storage**, set storage to at least `50GB`.
12. Click **Launch instance**.
13. After the instance starts, select it in the EC2 instance list and record:
    - **Instance ID**
    - **Public IPv4 DNS** or **Public IPv4 address**
    - **VPC ID**
    - **Subnet ID**
    - **Host security group ID**

You will use the host instance's **Subnet ID** as `AWS_SUBNET_ID` and create a separate client security group in Step 3 as `AWS_SECURITY_GROUP_ID`. The host and client instances must be in the same subnet, and the client security group must be created in the same VPC as that subnet. If you do not see a default VPC in `us-east-1`, create the AWS default VPC in the VPC console before continuing, then use that VPC and one of its subnets for both the host and client setup.

#### Step 2: Connect to Host Instance

1. Download the `.pem` key file when creating the instance
2. Set permissions:
   ```bash
   chmod 400 <your_key_file_path>
   ```
3. Connect via SSH:
   ```bash
   ssh -i <your_key_path> ubuntu@<your_public_dns>
   ```

Example:

```bash
chmod 400 ~/Downloads/rogue-host-key.pem
ssh -i ~/Downloads/rogue-host-key.pem ubuntu@ec2-xx-xx-xx-xx.compute-1.amazonaws.com
```

If the public DNS name is not shown in the AWS Console, use the host instance's public IPv4 address instead:

```bash
ssh -i ~/Downloads/rogue-host-key.pem ubuntu@<your_public_ipv4_address>
```

##### Install Host Dependencies

A fresh Ubuntu EC2 host does not include Miniconda or the build tools that some Python packages need.

1. Install the system packages used by the Python environment:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-dev gcc linux-headers-$(uname -r)
   ```
2. Install Miniconda for Linux x86_64, which matches the host instance types in this guide:
   ```bash
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   bash Miniconda3-latest-Linux-x86_64.sh
   ```
   Accept the default install location (`~/miniconda3`) and let the installer initialize conda.
3. Reload your shell so `conda` is available:
   ```bash
   source ~/.bashrc
   ```
4. Verify the install:
   ```bash
   conda --version
   ```

If this repository is not already on the host instance, clone it and install dependencies there before running evaluations. The main README recommends Conda with Python 3.12:

```bash
git clone https://github.com/neuroagents-lab/ROGUE.git
cd ROGUE

conda create -n rogue python=3.12
conda activate rogue

python -m pip install -U pip
python -m pip install -r requirements.txt
```

If you are working from a fork or private copy, replace the repository URL and directory name accordingly.

#### Step 3: Configure AWS Client Machines

##### Security Group Configuration

Create a separate security group for the client virtual machines. This is the security group whose ID should be exported as `AWS_SECURITY_GROUP_ID`.

The evaluation environment requires certain ports to be open, such as port 5000 for backend connections, port 5910 for VNC visualization, port 9222 for Chrome control, etc. The `AWS_SECURITY_GROUP_ID` variable represents the security group configuration for virtual machines serving as evaluation environments. Please complete the configuration and set this environment variable to the ID of the configured security group.

**⚠️ Important**: Please strictly follow the port settings below to prevent tasks from failing due to connection issues:

To create the client security group:

1. In the AWS Console, go to **EC2**.
2. In the left sidebar, click **Security Groups**.
3. Click **Create security group**.
4. Set **Security group name** to something recognizable, such as `rogue-client-sg`.
5. Set **Description** to something like `ROGUE client VM security group`.
6. Set **VPC** to the same VPC ID as the host instance.
7. Add the inbound rules below.
8. Leave outbound traffic as all traffic to `0.0.0.0/0`.
9. Click **Create security group**.
10. Record the new security group ID, which should look like `sg-xxxxxxxxxxxxxxxxx`.

**Inbound Rules** (8 rules required):

| Type       | Protocol | Port Range | Source         | Description                |
|------------|----------|------------|----------------|----------------------------|
| SSH        | TCP      | 22         | 0.0.0.0/0      | SSH access                 |
| HTTP       | TCP      | 80         | 172.31.0.0/16  | HTTP traffic               |
| Custom TCP | TCP      | 5000       | 172.31.0.0/16  | OSWorld backend service    |
| Custom TCP | TCP      | 5910       | 0.0.0.0/0      | NoVNC visualization port   |
| Custom TCP | TCP      | 8006       | 172.31.0.0/16  | VNC service port           |
| Custom TCP | TCP      | 8080       | 172.31.0.0/16  | VLC service port           |
| Custom TCP | TCP      | 8081       | 172.31.0.0/16  | Additional service port    |
| Custom TCP | TCP      | 9222       | 172.31.0.0/16  | Chrome control port        |

**Outbound Rules** (1 rule required):

| Type        | Protocol | Port Range | Destination | Description                 |
|-------------|----------|------------|-------------|----------------------------|
| All traffic | All      | All        | 0.0.0.0/0   | Allow all outbound traffic |

Record the `AWS_SECURITY_GROUP_ID`.

Make sure the recorded security group belongs to the same VPC as the host subnet. The security group source ranges in this guide use `172.31.0.0/16` for the default VPC.

##### AWS Access Keys

This guide follows the environment-variable setup style used by OSWorld.

1. In the AWS Console, click your account name in the top-right corner.
2. Choose **Security credentials**.
3. In the access keys section, click **Create access key**.
4. Record `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

AWS shows the secret access key only once. Copy it when it is created.

The AWS identity used by these keys must be allowed to create, describe, start, stop, and terminate EC2 instances. If TTL auto-termination is enabled, the code may also use EventBridge Scheduler and IAM role permissions.

If your AWS account uses restricted IAM permissions, ask for access to at least the EC2 actions needed by the provider:

- `ec2:RunInstances`
- `ec2:DescribeInstances`
- `ec2:StartInstances`
- `ec2:StopInstances`
- `ec2:TerminateInstances`
- `ec2:CreateImage`

For TTL auto-termination, the code may also need:

- `scheduler:CreateSchedule`
- `sts:GetCallerIdentity`
- `iam:GetRole`
- `iam:CreateRole`
- `iam:UpdateAssumeRolePolicy`
- `iam:GetRolePolicy`
- `iam:PutRolePolicy`

Do not commit AWS access keys to the repository.

If the account uses a restricted IAM setup and you need the TTL cleanup feature, also make sure the identity can manage the EventBridge Scheduler and the IAM role used by the scheduler.

#### Step 4: Set Up Host Machine

##### Set Environment Variables

Set the following environment variables on the host machine before running AWS evaluations. You can add these to `~/.bashrc` for persistence.

```bash
# API Keys (if using)
# export OPENAI_API_KEY="your_openai_api_key"
# export ANTHROPIC_API_KEY="your_anthropic_api_key"

# AWS Configuration
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_access_key"
export AWS_REGION="us-east-1"
export AWS_SECURITY_GROUP_ID="sg-xxxx"
export AWS_SUBNET_ID="subnet-xxxx"
```

Optional AWS provider variables that the code understands:

```bash
export AWS_INSTANCE_TYPE="t3.xlarge"
export DEFAULT_TTL_MINUTES="180"
export ENABLE_TTL="true"
export AWS_SCHEDULER_ROLE_ARN=""
export AWS_SCHEDULER_ROLE_NAME="osworld-scheduler-ec2-terminate"
export AWS_AUTO_CREATE_SCHEDULER_ROLE="true"
```

You only need the TTL variables if you want the code to auto-terminate instances after a fixed time. If you leave them unset, the defaults in the code are used.

Example with persistent shell configuration:

```bash
nano ~/.bashrc
```

Add the exports above to the end of the file, save it, then reload the shell configuration:

```bash
source ~/.bashrc
```

Check that the variables are present:

```bash
echo "$AWS_REGION"
echo "$AWS_SECURITY_GROUP_ID"
echo "$AWS_SUBNET_ID"
```

##### Code Configuration Variables

The AWS provider code may also reference configuration values such as `DEFAULT_REGION`, `IMAGE_ID_MAP`, `INSTANCE_TYPE`, `KEY_NAME`, and `NETWORK_INTERFACES`. Make sure these match your selected region, AMI, key pair, subnet, and security group.

In the current AWS manager implementation:

- `DEFAULT_REGION` is `us-east-1`
- `IMAGE_ID_MAP` contains the AMI IDs listed in Step 0
- `INSTANCE_TYPE` for launched client VMs is `t3.xlarge`
- `AWS_INSTANCE_TYPE` can override the instance type during snapshot revert
- `AWS_REGION`, `AWS_SUBNET_ID`, and `AWS_SECURITY_GROUP_ID` must be present in the environment

You usually do not need to edit these code-level variables for a first-time `us-east-1` setup. Edit them only if you are changing regions, AMIs, instance types, key-pair behavior, or network interface behavior.

#### Step 5: Verify the AWS Setup

Run these checks on the host machine after setting the environment variables.

First, confirm the variables are set:

```bash
test -n "$AWS_ACCESS_KEY_ID" && echo "AWS_ACCESS_KEY_ID is set"
test -n "$AWS_SECRET_ACCESS_KEY" && echo "AWS_SECRET_ACCESS_KEY is set"
test -n "$AWS_REGION" && echo "AWS_REGION=$AWS_REGION"
test -n "$AWS_SECURITY_GROUP_ID" && echo "AWS_SECURITY_GROUP_ID=$AWS_SECURITY_GROUP_ID"
test -n "$AWS_SUBNET_ID" && echo "AWS_SUBNET_ID=$AWS_SUBNET_ID"
```

Then, if the AWS CLI is installed, confirm AWS can see the account, subnet, and security group:

```bash
aws sts get-caller-identity
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$AWS_SUBNET_ID"
aws ec2 describe-security-groups --region "$AWS_REGION" --group-ids "$AWS_SECURITY_GROUP_ID"
```

The subnet and security group checks should both succeed in `us-east-1`. If either command fails, fix the region, subnet ID, security group ID, or AWS credentials before running an evaluation.

#### Step 6: Run an AWS Evaluation

After AWS is configured, run evaluations with `--provider_name aws`, the same region used above, and `osworld-public-evaluation` as the AWS VM password.

Example:

```bash
python scripts/python/run_multienv.py \
  --provider_name aws \
  --headless \
  --action_space pyautogui \
  --observation_type screenshot \
  --model <MODEL_NAME> \
  --reasoning_effort medium \
  --max_steps 20 \
  --max_trajectory_length 20 \
  --per-step-recording \
  --test_all_meta_path evaluation_examples/test_override.json \
  --result_dir ./results/override/base \
  --num_envs 5 \
  --region us-east-1 \
  --client_password osworld-public-evaluation
```

**Key Parameters**:
- `--num_envs`: Number of parallel environments
- `--max_steps`: Maximum steps per task
- `--result_dir`: Output directory for results
- `--test_all_meta_path`: Path to test set metadata
- `--region`: AWS region

You can also use the documented experiment runner:

```bash
scripts/experiment_runner.sh list
scripts/experiment_runner.sh override_base_all
scripts/experiment_runner.sh rewire_base_all
scripts/experiment_runner.sh restrictedaccess_base_all
```

##### Monitoring and Results

###### Web Monitoring Tool

```bash
cd monitor
python -m pip install -r requirements.txt
python main.py
```

Access at: `http://<host-public-ip>:8080`

###### VNC Remote Desktop Access

Access VMs via VNC at: `http://<client-public-ip>:5910/vnc.html`

Default password: `osworld-public-evaluation`

###### Aggregate Results

```bash
python scripts/aggregate_results.py \
    --results_root ./results \
    --judge-mode cache_only
```

Use `--judge-mode auto` to reuse cached judgments and fill missing judgments through the OpenAI API.

### Troubleshooting

#### `AWS_REGION must be set in the environment variables`

Set `AWS_REGION` on the host machine:

```bash
export AWS_REGION="us-east-1"
```

#### `AWS_SUBNET_ID and AWS_SECURITY_GROUP_ID must be set`

Set both values on the host machine:

```bash
export AWS_SECURITY_GROUP_ID="sg-xxxx"
export AWS_SUBNET_ID="subnet-xxxx"
```

#### Client instance launch fails with a VPC or network interface error

Check that:

1. The subnet ID is from the host instance.
2. The client security group is in the same VPC as that subnet.
3. The AWS Console region matches `AWS_REGION`.
4. The security group inbound rules exactly match the table above.

#### VNC URL does not open

Check that:

1. The client instance has a public IPv4 address.
2. The client security group allows TCP port `5910` from `0.0.0.0/0`.
3. The instance is still running.
4. The URL uses port `5910`, for example `http://<public-ip>:5910/vnc.html`.

#### AWS quota or capacity errors

Reduce `--num_envs`, use a smaller host workload, or request a quota increase for the selected EC2 instance type in `us-east-1`.

#### Unexpected AWS charges

Stop or terminate unused EC2 instances, snapshots, AMIs, volumes, and scheduler resources from the AWS Console. Review running instances before and after large parallel evaluations.

### Miscellaneous

The AWS VM password is `osworld-public-evaluation`.

### Disclaimer
AWS resources created by this setup may incur charges. Review instance types, storage, running time, and network usage before launching large parallel evaluations.
