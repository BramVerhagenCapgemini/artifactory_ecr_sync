#!/bin/bash
set -e

echo "Building Lambda deployment package..."
./build_lambda.sh

echo "Deploying with Terraform..."
cd ../../environments/dev/

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply deployment
terraform apply -auto-approve

echo "Deployment complete!"