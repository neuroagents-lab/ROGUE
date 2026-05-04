# ROGUE Setup and Evaluation Guide

This guide covers account configuration and AWS public evaluation platform deployment for ROGUE. The environment and VM setup are inherited from OSWorld-Verified, so the platform details remain closely aligned with OSWorld.

## Table of Contents

1. [Google Account Setup](#1-google-account-setup)
2. [Public Evaluation Platform](#2-public-evaluation-platform)

---

## 1. Google Account Setup

For tasks including Google or Google Drive, you need a real Google account with configured OAuth2.0 secrets.

> **Attention**: To prevent environment reset and result evaluation conflicts caused by multiple people using the same Google account simultaneously, please register a private Google account rather than using a shared one.

### 1.1 Register A Blank Google Account

1. Go to Google website and register a blank new account
   - You do not need to provide any recovery email or phone for testing purposes
   - **IGNORE** any security recommendations
   - Turn **OFF** the [2-Step Verification](https://support.google.com/accounts/answer/1064203?hl=en&co=GENIE.Platform%3DDesktop#:~:text=Open%20your%20Google%20Account.,Select%20Turn%20off.) to avoid failure in environment setup

> **Attention**: We strongly recommend registering a new blank account instead of using an existing one to avoid messing up your personal workspace.

2. Copy and rename `settings.json.template` to `settings.json` under `evaluation_examples/settings/google/`. Replace the two fields:

```json
{
    "email": "your_google_account@gmail.com",
    "password": "your_google_account_password"
}
```

### 1.2 Create A Google Cloud Project

1. Navigate to [Google Cloud Project Creation](https://console.cloud.google.com/projectcreate) and create a new GCP (see [Create a Google Cloud Project](https://developers.google.com/workspace/guides/create-project) for detailed steps)

2. Go to the [Google Drive API console](https://console.cloud.google.com/apis/library/drive.googleapis.com?) and enable the Google Drive API for the created project (see [Enable and disable APIs](https://support.google.com/googleapi/answer/6158841?hl=en))

### 1.3 Configure OAuth Consent Screen

Go to [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent):

1. Select **External** as the User Type and click **CREATE**

2. Fill in the required fields:
   - **App name**: Any name you prefer
   - **User support email**: Your Google account email
   - **Developer contact information**: Your Google account email
   - Click **SAVE AND CONTINUE**

3. Add scopes:
   - Click **ADD OR REMOVE SCOPES**
   - Filter and select: `https://www.googleapis.com/auth/drive`
   - Click **UPDATE** and **SAVE AND CONTINUE**

4. Add test users:
   - Click **ADD USERS**
   - Add your Google account email
   - Click **SAVE AND CONTINUE**

### 1.4 Create OAuth2.0 Credentials

1. Go to [Credentials](https://console.cloud.google.com/apis/credentials) page
2. Click **CREATE CREDENTIALS** -> **OAuth client ID**
3. Select **Desktop app** as Application type
4. Name it (e.g., "ROGUE Desktop Client")
5. Click **CREATE**

6. Download the JSON file.
7. Place it at:

```text
evaluation_examples/settings/googledrive/client_secrets.json
```

The existing PyDrive settings file is:

```text
evaluation_examples/settings/googledrive/settings.yml
```

It stores OAuth credentials at:

```text
evaluation_examples/settings/googledrive/credentials.json
```

If you need to refresh the stored credentials, run:

```bash
python - <<'PY'
from pydrive.auth import GoogleAuth

settings_file = "evaluation_examples/settings/googledrive/settings.yml"
credentials_file = "evaluation_examples/settings/googledrive/credentials.json"

gauth = GoogleAuth(settings_file=settings_file)
gauth.LocalWebserverAuth()
gauth.SaveCredentialsFile(credentials_file)
PY
```

### 1.5 Potential Issues

#### Issue 1: Access Blocked During OAuth Flow

**Symptom**: "Access blocked: OSWorld's request is invalid" error

**Solution**: Ensure you've added your Google account as a test user in the OAuth consent screen configuration.

#### Issue 2: Scope Not Granted

**Symptom**: Application doesn't have necessary permissions

**Solution**: Verify that `https://www.googleapis.com/auth/drive` scope is added in the OAuth consent screen.

---

## 2. Public Evaluation Platform

We provide an AWS-based platform for large-scale parallel evaluation of ROGUE tasks.

### 2.1 Architecture Overview

- **Host Instance**: Central controller that stores code, configurations, and manages task execution
- **Client Instances**: Worker nodes automatically launched to perform tasks in parallel

### 2.2 Platform Deployment

#### Step 1: Launch the Host Instance

1. Create an EC2 instance in AWS console
2. **Instance type recommendations**:
   - `t3.medium`: For < 5 parallel environments
   - `t3.large`: For < 15 parallel environments
   - `c4.8xlarge`: For 15+ parallel environments
3. **AMI**: Ubuntu Server 24.04 LTS (HVM), SSD Volume Type
4. **Storage**: At least 50GB
5. **Security group**: Open port 8080 for monitor service
6. **VPC**: Use default (note the VPC ID for later)

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

#### Step 3: Set Up Host Machine

```bash
# Clone ROGUE repository
git clone https://github.com/neuroagents-lab/OSWorld-Corrigibility.git
cd OSWorld-Corrigibility

# Create Conda environment
conda create -n rogue python=3.12
conda activate rogue

# Install dependencies
python -m pip install -U pip
python -m pip install -r requirements.txt
```

#### Step 4: Configure AWS Client Machines

##### Security Group Configuration

Create a security group with the following rules:

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

##### VPC and Subnet Configuration

1. Note the **VPC ID** and **Subnet ID** from your host instance
2. Record the **Subnet ID** as `AWS_SUBNET_ID`

##### AWS Access Keys

1. Go to AWS Console -> Security Credentials
2. Create access key
3. Record `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

### 2.3 Environment Setup

#### Google Drive Integration (Optional)

Follow [Section 1: Google Account Setup](#1-google-account-setup) above.

Some ROGUE tasks require Google Drive. You can either complete Google Drive setup or skip tasks that depend on it.

#### Set Environment Variables

```bash
# API Keys (if using)
# export OPENAI_API_KEY="your_openai_api_key"
# export ANTHROPIC_API_KEY="your_anthropic_api_key"

# AWS Configuration
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_security_access_key"
export AWS_REGION="us-east-1"  # or your preferred region
export AWS_SECURITY_GROUP_ID="sg-xxxx"
export AWS_SUBNET_ID="subnet-xxxx"
```

### 2.4 Running Evaluations

```bash
# Example: Run a ROGUE override sweep on AWS
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --result_dir ./results/override/base \
    --test_all_meta_path evaluation_examples/test_override.json \
    --region us-east-1 \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --num_envs 5 \
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

### 2.5 Monitoring and Results

#### Web Monitoring Tool

```bash
cd monitor
python -m pip install -r requirements.txt
python main.py
```

Access at: `http://<host-public-ip>:8080`

#### VNC Remote Desktop Access

Access VMs via VNC at: `http://<client-public-ip>:5910/vnc.html`

Default password: `osworld-public-evaluation`

#### Aggregate Results

```bash
python scripts/aggregate_results.py \
    --results_root ./results \
    --judge-mode cache_only
```

Use `--judge-mode auto` to reuse cached judgments and fill missing judgments through the OpenAI API.

---

## Additional Resources

- [Main README](README.md) - Project overview and quick start
- [AWS Provider Guide](desktop_env/providers/aws/AWS_GUIDELINE.md) - Lower-level AWS provider configuration

## Support

If you encounter issues or have questions, open an issue on the project repository or contact the project maintainers.
