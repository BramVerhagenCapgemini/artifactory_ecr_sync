variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "function_name" {
  description = "Lambda function name"
  type        = string
  default     = "artifactory-ecr-sync"
}

variable "lambda_image_uri" {
  description = "URI of the Lambda container image (if already built)"
  type        = string
  default     = ""
}

variable "artifactory_url" {
  description = "Artifactory URL"
  type        = string
  default     = ""
}

variable "artifactory_repo" {
  description = "Artifactory repository path"
  type        = string
  default     = ""
}

variable "credentials_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret containing Artifactory credentials"
  type        = string
}

variable "ecr_registry" {
  description = "ECR registry URL"
  type        = string
}

variable "image_filters" {
  description = "Comma-separated image filters"
  type        = string
  default     = ""
}

variable "tag_filters" {
  description = "Comma-separated tag filters"
  type        = string
  default     = ""
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (e.g., 'rate(1 hour)')"
  type        = string
  default     = ""
}

variable "permissions_boundary_arn" {
  description = "ARN of the permissions boundary policy"
  type        = string
  default     = null
}