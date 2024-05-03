# make region variable to user
# NOTE: user needs to have AWS credentials stored in environment variables!
variable "aws_region" {
  type = string
  description = "Provide the AWS region the architecture should be deployed in."
}

variable "bucket" {
  type = string
  description = "Provide the name of your S3 bucket."
}

variable "token" {
  type = string
  description = "Provide the desired name of your Oauth token in Secrets Manager."
}

variable "email" {
  type = string
  description = "Please enter the e-mail address which should receive error notifications."
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

module "dynamodb" {
  source = "./terraform_modules/dynamodb"
  reports = ["channel_basic_a2_1", "channel_combined_a2_1", "channel_demographics_a1_1", "channel_sharing_service_a1_1"]
}

module "secret" {
  source = "./terraform_modules/secretsmanager"
  token = var.token
}

module "lambda" {
  source = "./terraform_modules/lambda"
  bucket = var.bucket
  table_arns = module.dynamodb.table_arns
  depends_on = [ module.dynamodb, module.secret ]
  secret_arn = module.secret.secret_arn
  email = var.email
  account_id = data.aws_caller_identity.current.account_id
}
