# make region variable to user
# NOTE: user needs to have AWS credentials stored in environment variables!
variable "aws_region" {
  type = string
}

provider "aws" {
  region = var.aws_region
}

module "dynamodb" {
  source = "./terraform_modules/dynamodb"
  reports = ["channel_basic_a2", "channel_combined_a2", "channel_demographics_a1", "channel_sharing_service_a1"]
}