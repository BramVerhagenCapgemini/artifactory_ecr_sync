# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name                 = "${var.function_name}-role"
  permissions_boundary = var.permissions_boundary_arn

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },

    ]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.function_name}-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeRepositories",
          "ecr:CreateRepository",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = var.credentials_secret_arn
      }
    ]
  })
}

# ECR Repository for Lambda container image
resource "aws_ecr_repository" "lambda_image" {
  name = "${var.function_name}-image"
}

# Lambda Function
resource "aws_lambda_function" "sync_function" {
  function_name    = var.function_name
  role            = aws_iam_role.lambda_role.arn
  package_type    = "Zip"
  filename        = "${path.module}/../../scripts/artifactory_ecr_sync/lambda-deployment.zip"
  handler         = "lambda_handler.lambda_handler"
  runtime         = "python3.12"
  source_code_hash = filebase64sha256("${path.module}/../../scripts/artifactory_ecr_sync/lambda-deployment.zip")
  timeout         = 900
  memory_size     = 2048
  
  ephemeral_storage {
    size = 2048
  }
  

  environment {
    variables = {
      ARTIFACTORY_URL           = var.artifactory_url
      ARTIFACTORY_REPO          = var.artifactory_repo
      ECR_REGION               = var.aws_region
      ECR_REGISTRY             = var.ecr_registry
      IMAGE_FILTERS            = var.image_filters
      TAG_FILTERS              = var.tag_filters
      CREDENTIALS_SECRET_ARN   = var.credentials_secret_arn
    }
  }
}

# EventBridge Rule for scheduling
resource "aws_cloudwatch_event_rule" "sync_schedule" {
  for_each            = var.schedule_expression != "" ? { enabled = true } : {}
  name                = "${var.function_name}-schedule"
  description         = "Trigger sync function"
  schedule_expression = var.schedule_expression
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "lambda_target" {
  for_each  = var.schedule_expression != "" ? { enabled = true } : {}
  rule      = aws_cloudwatch_event_rule.sync_schedule["enabled"].name
  target_id = "SyncLambdaTarget"
  arn       = aws_lambda_function.sync_function.arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  for_each      = var.schedule_expression != "" ? { enabled = true } : {}
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sync_function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sync_schedule["enabled"].arn
}