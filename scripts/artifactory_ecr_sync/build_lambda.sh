#!/bin/bash
set -e

# Create build directory
rm -rf build/
mkdir -p build/

# Install dependencies
pip install -r requirements-lambda.txt -t build/

# Copy source files
cp lambda_handler.py build/lambda_handler.py

# Create deployment package
cd build/
zip -r ../lambda-deployment.zip .
cd ..

# Clean up build directory
rm -rf build/

echo "Lambda deployment package created: lambda-deployment.zip"