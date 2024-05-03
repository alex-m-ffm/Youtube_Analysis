# upload packaged lambda code
variable "bucket" {
  type = string
}

variable "account_id" {
  type = string
}

variable "email" {
  type = string
}

variable "table_arns" {
  type = list(string)
}

variable "secret_arn" {
  type = string
}

module "iam_module" {
  source = "./iam_module"
  table_arns = var.table_arns
  secret_arn = var.secret_arn
  account_id = var.account_id
}

module "sns" {
  source = "./sns"
  email = var.email
  account_id = var.account_id
  iam_role_lambda_process_name = module.iam_module.lambda_process_role_name
  iam_role_lambda_clean_name = module.iam_module.lambda_clean_role_name
  depends_on = [ module.iam_module ]
}

resource "aws_s3_object" "lambda_process" {
  bucket = var.bucket
  key    = "files/lambda.zip"
  source = "lambda.zip"

  etag = filemd5("lambda.zip")
}

resource "aws_s3_object" "lambda_clean" {
  bucket = var.bucket
  key    = "files/lambda_clean.zip"
  source = "lambda_clean.zip"
  
  etag = filemd5("lambda_clean.zip")
}

# now let's create the lambda function based on the S3 object and assign the necessary execution roles

resource "aws_lambda_function" "lambda_process" {
  s3_bucket     = var.bucket
  s3_key        = aws_s3_object.lambda_process.key
  function_name = "DailyProcessing"
  description = "Daily processing of YouTube Data"
  handler       = "lambda_function.lambda_handler"
  runtime        = "python3.12"
  role           = module.iam_module.lambda_process_role_arn
  timeout = 900
  }

resource "aws_lambda_function" "lambda_clean" {
  s3_bucket     = var.bucket
  s3_key        = aws_s3_object.lambda_clean.key
  function_name = "MonthlyCleaning"
  description = "Monthly cleaning of DynamyDB"
  handler       = "lambda_clean_dynamodb.lambda_handler"
  runtime        = "python3.12"
  role           = module.iam_module.lambda_clean_role_arn
  timeout = 900
  depends_on = [ module.sns ]
  }

resource "aws_lambda_function_event_invoke_config" "lambda_process_destination" {
  function_name = aws_lambda_function.lambda_process.function_name

  destination_config {
    on_failure {
      destination = module.sns.sns_process_errors_arn
    }
  }
}

resource "aws_lambda_function_event_invoke_config" "lambda_clean_destination" {
  function_name = aws_lambda_function.lambda_clean.function_name

  destination_config {
    on_failure {
      destination = module.sns.sns_cleanup_errors_arn
    }
  }
}

module "eventbridge" {
  source = "./eventbridge"
  account_id = var.account_id
  lambda_clean_arn = aws_lambda_function.lambda_clean.arn
  lambda_process_arn = aws_lambda_function.lambda_process.arn
}
