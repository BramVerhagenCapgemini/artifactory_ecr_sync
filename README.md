# Artifactory to ECR Sync

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Terraform](https://img.shields.io/badge/terraform-%235835CC.svg?style=flat&logo=terraform&logoColor=white)](https://www.terraform.io/)

Automated synchronization of container images from JFrog Artifactory to Amazon Elastic Container Registry (ECR) using AWS Lambda.

## ⚠️ Disclaimer

**This is a personal experiment and NOT production-ready code.**

- This project is provided as-is for educational and experimental purposes
- No warranties or guarantees of any kind are provided
- Use at your own risk and responsibility
- Further development, modification, and deployment are entirely at your own discretion
- The author assumes no liability for any issues arising from the use of this code
- Always review and test thoroughly before using in any environment

### License Scope

The MIT License applies to:
- Original source code in this repository
- Terraform configuration files
- Documentation and scripts

Third-party dependencies retain their original licenses. See [Dependencies](#dependencies) section for details.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Cost Estimation](#cost-estimation)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

This project provides an automated solution for synchronizing Docker container images from JFrog Artifactory to AWS ECR. It uses AWS Lambda to periodically check for new images in Artifactory and sync them to ECR using Docker Registry V2 API and AWS ECR API.

### Why This Project?

- **Hybrid Cloud Strategy**: Bridge on-premises Artifactory with AWS ECR
- **Cost Optimization**: Reduce data transfer costs by syncing only needed images
- **Automation**: Eliminate manual image copying between registries
- **Serverless**: No infrastructure to manage, pay only for what you use

## ✨ Features

- 🔄 **Automated Sync**: Scheduled synchronization using EventBridge
- 🎯 **Selective Sync**: Filter images and tags using configurable patterns
- 🔐 **Secure**: Credentials stored in AWS Secrets Manager
- 📦 **API-Based**: Uses Docker Registry V2 API (no Docker CLI required)
- 🏗️ **Auto-Create Repositories**: Automatically creates ECR repositories as needed
- 📊 **Detailed Logging**: CloudWatch Logs integration for monitoring
- 🚀 **Serverless**: Runs on AWS Lambda with minimal overhead
- 💰 **Cost-Effective**: Small deployment package, fast execution

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Artifactory   │         │   AWS Lambda     │         │    Amazon ECR   │
│                 │         │                  │         │                 │
│  Docker Images  │────────>│  Sync Function   │────────>│  Docker Images  │
│                 │  HTTP   │                  │  boto3  │                 │
└─────────────────┘  API    └──────────────────┘  API    └─────────────────┘
                                     │
                                     │
                            ┌────────▼─────────┐
                            │  AWS Secrets     │
                            │  Manager         │
                            │  (Credentials)   │
                            └──────────────────┘
                                     │
                            ┌────────▼─────────┐
                            │  EventBridge     │
                            │  (Scheduler)     │
                            └──────────────────┘
```

### How It Works

1. **EventBridge** triggers Lambda on a schedule (e.g., hourly)
2. **Lambda** retrieves Artifactory credentials from Secrets Manager
3. **Lambda** queries Artifactory for available images and tags
4. **Lambda** filters images/tags based on configured patterns
5. **Lambda** downloads image manifests and layers via HTTP API
6. **Lambda** pushes images to ECR using boto3 API
7. **Lambda** logs results to CloudWatch

## 📦 Prerequisites

- **AWS Account** with appropriate permissions
- **Terraform** >= 1.0
- **Python** 3.12 (for local development)
- **JFrog Artifactory** instance with Docker registry
- **AWS CLI** configured (optional, for manual testing)

### Required AWS Permissions

- Lambda: Create and manage functions
- ECR: Create repositories, push images
- Secrets Manager: Read secrets
- IAM: Create roles and policies
- EventBridge: Create rules
- CloudWatch Logs: Create log groups

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd artifactory_ecr_sync
```

### 2. Create Secrets in AWS Secrets Manager

Create a secret containing your Artifactory credentials:

```bash
aws secretsmanager create-secret \
  --name ArtifactoryCredentials \
  --secret-string '{
    "username": "your-username",
    "tokenId": "your-token-id",
    "tokenSecret": "your-token-secret"
  }'
```

Note the ARN of the created secret.

### 3. Build Lambda Deployment Package

```bash
cd scripts/artifactory_ecr_sync
./build_lambda.sh
```

This creates `lambda-deployment.zip` containing the function code and dependencies.

## ⚙️ Configuration

### Terraform Variables

Create a `terraform.tfvars` file in your environment directory:

```hcl
# Required variables
credentials_secret_arn = "arn:aws:secretsmanager:<region>:<account-id>:secret:<secret-name>"
ecr_registry          = "<account-id>.dkr.ecr.<region>.amazonaws.com"

# Optional variables
aws_region            = "us-east-1"
function_name         = "artifactory-ecr-sync"
artifactory_url       = "https://your-artifactory.example.com/artifactory"
artifactory_repo      = "docker-repo"
image_filters         = "app,service"  # Comma-separated
tag_filters           = "latest,v*"    # Comma-separated
schedule_expression   = "rate(1 hour)" # EventBridge schedule
permissions_boundary_arn = null        # Optional IAM boundary
```

### Environment Variables

The Lambda function uses these environment variables (set by Terraform):

| Variable | Description | Required |
|----------|-------------|----------|
| `ARTIFACTORY_URL` | Artifactory base URL | Yes |
| `ARTIFACTORY_REPO` | Docker repository name | Yes |
| `ECR_REGION` | AWS region for ECR | Yes |
| `ECR_REGISTRY` | ECR registry URL | Yes |
| `CREDENTIALS_SECRET_ARN` | Secrets Manager ARN | Yes |
| `IMAGE_FILTERS` | Comma-separated image filters | No |
| `TAG_FILTERS` | Comma-separated tag filters | No |

### Filtering

**Image Filters**: Only sync images whose names contain any of the filter strings
```
IMAGE_FILTERS=app,service
# Matches: my-app, web-service, app-backend
# Skips: database, cache
```

**Tag Filters**: Only sync tags that contain any of the filter strings
```
TAG_FILTERS=latest,v1,prod
# Matches: latest, v1.0, v1.2.3, prod-release
# Skips: dev, test, staging
```

## 🎯 Usage

### Deploy with Terraform

```bash
cd module

# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Deploy
terraform apply
```

### Manual Invocation

Test the Lambda function manually:

```bash
aws lambda invoke \
  --function-name artifactory-ecr-sync \
  --payload '{}' \
  response.json

cat response.json
```

### Custom Event Payload

Override configuration at runtime:

```bash
aws lambda invoke \
  --function-name artifactory-ecr-sync \
  --payload '{
    "artifactory_repo": "custom-repo",
    "image_filters": "specific-app",
    "tag_filters": "v2"
  }' \
  response.json
```

## 📊 Monitoring

### CloudWatch Logs

View logs in CloudWatch:

```bash
aws logs tail /aws/lambda/artifactory-ecr-sync --follow
```

### Metrics

The Lambda function returns:

```json
{
  "statusCode": 200,
  "body": {
    "message": "Synced 5 images, 1 failed",
    "successful": ["app:latest", "service:v1.0"],
    "failed": ["large-image:v2.0"]
  }
}
```

### CloudWatch Alarms

Set up alarms for:
- Lambda errors
- Lambda duration (approaching timeout)
- Failed image syncs

## 🔧 Troubleshooting

### Common Issues

**Issue**: Lambda timeout
- **Solution**: Increase timeout in Terraform (max 900 seconds)
- **Solution**: Reduce number of images synced per invocation

**Issue**: Out of memory
- **Solution**: Increase Lambda memory (currently 2048 MB)
- **Solution**: Filter to sync smaller images

**Issue**: Authentication failed
- **Solution**: Verify Secrets Manager secret format
- **Solution**: Check Artifactory token permissions

**Issue**: ECR repository not found
- **Solution**: Function auto-creates repositories, check IAM permissions

**Issue**: Image not syncing
- **Solution**: Check image/tag filters
- **Solution**: Verify image exists in Artifactory

### Debug Mode

Enable debug logging by modifying `lambda_handler.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 💰 Cost Estimation

**Assumptions**:
- 50 images synced per day
- Average image size: 200 MB
- Sync duration: 20 seconds per image
- Lambda memory: 2048 MB

**Monthly Costs**:
- Lambda compute: ~$2.50
- Lambda requests: ~$0.01
- ECR storage: Variable (depends on images stored)
- Data transfer: Variable (depends on image sizes)

**Total Lambda cost**: ~$2.51/month

*Note: ECR storage and data transfer costs depend on your usage patterns.*

## 🤝 Contributing

This is a personal experiment, but contributions are welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Remember**: Any contributions are also provided without warranty. Contributors assume no liability.

## 📦 Dependencies

This project uses the following third-party libraries and tools:

### Python Libraries
- [boto3](https://github.com/boto/boto3) - Apache 2.0 License - AWS SDK for Python
- [requests](https://github.com/psf/requests) - Apache 2.0 License - HTTP library for Python

### Infrastructure Tools
- [Terraform](https://www.terraform.io/) - Business Source License 1.1 - Infrastructure as Code
- [Terraform AWS Provider](https://github.com/hashicorp/terraform-provider-aws) - MPL 2.0 - AWS resource management

### AWS Services
- AWS Lambda - Serverless compute
- Amazon ECR - Container registry
- AWS Secrets Manager - Credential storage
- Amazon EventBridge - Scheduling
- Amazon CloudWatch - Logging and monitoring

All third-party dependencies retain their original licenses. This project's MIT License applies only to the original code, configuration, and documentation created for this repository.

## 📦 Module Usage

If using as a Terraform module:

```hcl
module "artifactory_ecr_sync" {
  source = "./module"

  aws_region             = "us-east-1"
  function_name          = "artifactory-ecr-sync"
  artifactory_url        = "https://your-artifactory.example.com/artifactory"
  artifactory_repo       = "docker-repo"
  credentials_secret_arn = "arn:aws:secretsmanager:<region>:<account-id>:secret:<secret-name>"
  ecr_registry           = "<account-id>.dkr.ecr.<region>.amazonaws.com"
  image_filters          = "app,service"
  tag_filters            = "latest,v*"
  schedule_expression    = "rate(1 hour)"
}
```

### Module Outputs

| Name | Description |
|------|-------------|
| lambda_function_arn | ARN of the Lambda function |
| lambda_function_name | Name of the Lambda function |

## 🔗 Related Resources

- [Docker Registry HTTP API V2](https://docs.docker.com/registry/spec/api/)
- [AWS ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Final Note

**This code is experimental and provided for educational purposes only.**

Before using this in any environment:
- Review all code thoroughly
- Test in a non-production environment
- Understand the security implications
- Ensure compliance with your organization's policies
- Monitor costs and usage carefully

**You are solely responsible for any use of this code.**

---

**Questions or Issues?** Open an issue on GitHub (understanding that support is provided on a best-effort basis with no guarantees).
