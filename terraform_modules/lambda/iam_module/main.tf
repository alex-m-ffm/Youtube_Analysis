variable "account_id" {
  type = string
}

variable "table_arns" {
  type = list(string)
}

variable "secret_arn" {
  type = string
}


resource "aws_iam_policy" "lambda_basic_execution" {
  name = "Basic_Execution_Role"
  description = "Policy for writing to CloudWatch Logs"

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
})
}

# create IAM policy to read and write from specific DynamoDB tables

resource "aws_iam_policy" "dynamodb_batch_access" {
  name        = "DynamoDB-Batch-Access"
  description = "Policy for batch accessing DynamoDB tables"

  policy      = jsonencode({
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"dynamodb:BatchGetItem",
				"dynamodb:BatchWriteItem",
				"dynamodb:PutItem",
				"dynamodb:DescribeTable",
				"dynamodb:DeleteItem",
				"dynamodb:GetItem",
				"dynamodb:Scan",
				"dynamodb:ListTagsOfResource",
				"dynamodb:Query",
				"dynamodb:UpdateItem",
				"dynamodb:UpdateTable",
				"dynamodb:GetRecords"
			],
			"Resource": var.table_arns
		},
		{
			"Sid": "VisualEditor1",
			"Effect": "Allow",
			"Action": "dynamodb:ListTables",
			"Resource": "*"
		}
	]
})
}

resource "aws_iam_policy" "secret_access" {
  name        = "Secret-Access"
  description = "Policy for accessing secrets managed in AWS Systems Manager Parameter Store"

  policy      = jsonencode({
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"ssm:GetParameter", 
        "ssm:PutParameter"
			],
			"Resource": var.secret_arn
		}
	]
})
}

resource "aws_iam_role" "lambda_process_role" {
  name        = "LambdaExecutionRoleProcessing"
  description = "IAM role for the Processing Function"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role" "lambda_clean_role" {
  name        = "LambdaExecutionRoleCleaning"
  description = "IAM role for the Cleaning Function"

  assume_role_policy = jsonencode({
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
})
}

resource "aws_iam_role_policy_attachment" "attach_basic_process" {
  role       = aws_iam_role.lambda_process_role.name
  policy_arn = aws_iam_policy.lambda_basic_execution.arn
}

resource "aws_iam_role_policy_attachment" "attach_basic_clean" {
  role       = aws_iam_role.lambda_clean_role.name
  policy_arn = aws_iam_policy.lambda_basic_execution.arn
}


resource "aws_iam_role_policy_attachment" "attach_db_access_process" {
  role       = aws_iam_role.lambda_process_role.name
  policy_arn = aws_iam_policy.dynamodb_batch_access.arn
}

resource "aws_iam_role_policy_attachment" "attach_db_access_clean" {
  role       = aws_iam_role.lambda_clean_role.name
  policy_arn = aws_iam_policy.dynamodb_batch_access.arn
}

resource "aws_iam_role_policy_attachment" "attach_secret_access_process" {
  role       = aws_iam_role.lambda_process_role.name
  policy_arn = aws_iam_policy.secret_access.arn
}

output "lambda_process_role_name" {
  value = aws_iam_role.lambda_process_role.name
}

output "lambda_clean_role_name" {
  value = aws_iam_role.lambda_clean_role.name
}

output "lambda_process_role_arn" {
  value = aws_iam_role.lambda_process_role.arn
}

output "lambda_clean_role_arn" {
  value = aws_iam_role.lambda_clean_role.arn
}