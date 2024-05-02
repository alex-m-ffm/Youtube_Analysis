variable "account_id" {
  type = string
}

variable "email" {
  type = string
}

variable "iam_role_lambda_process_name" {
  type = string
}

variable "iam_role_lambda_clean_name" {
  type = string
}


resource "aws_sns_topic" "sns_process_errors" {
  name = "sns-process-errors"
}

resource "aws_sns_topic" "sns_cleanup_errors" {
  name = "sns-cleanup-errors"
}

resource "aws_iam_policy" "sns_topic_policy_process" {
  name        = "sns-topic-policy-process"
  description = "IAM policy for SNS topic process errors"
  policy      = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Action    = [
          "SNS:Subscribe",
          "SNS:SetTopicAttributes",
          "SNS:RemovePermission",
          "SNS:Receive",
          "SNS:Publish",
          "SNS:ListSubscriptionsByTopic",
          "SNS:GetTopicAttributes",
          "SNS:DeleteTopic",
          "SNS:AddPermission",
        ]
        Resource  = aws_sns_topic.sns_process_errors.arn
        Condition = {
          StringEquals = {
            "AWS:SourceOwner" = var.account_id
          }
        }
        Sid       = "default"
      }
    ]
  })
}

resource "aws_iam_policy" "sns_topic_policy_cleanup" {
  name        = "sns-topic-policy-cleanup"
  description = "IAM policy for SNS topic cleanup errors"
  policy      = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Action    = [
          "SNS:Subscribe",
          "SNS:SetTopicAttributes",
          "SNS:RemovePermission",
          "SNS:Receive",
          "SNS:Publish",
          "SNS:ListSubscriptionsByTopic",
          "SNS:GetTopicAttributes",
          "SNS:DeleteTopic",
          "SNS:AddPermission",
        ]
        Resource  = aws_sns_topic.sns_cleanup_errors.arn
        Condition = {
          StringEquals = {
            "AWS:SourceOwner" = var.account_id
          }
        }
        Sid       = "default"
      }
    ]
  })
}

#resource "aws_sns_topic_policy" "sns_process_policy" {
#  arn    = aws_sns_topic.sns_process_errors.arn
#  policy = aws_iam_policy.sns_topic_policy_process.policy
#}

#resource "aws_sns_topic_policy" "sns_cleanup_policy" {
#  arn    = aws_sns_topic.sns_cleanup_errors.arn
#  policy = aws_iam_policy.sns_topic_policy_cleanup.policy
#}

resource "aws_sns_topic_subscription" "user_receives_process_errors" {
  topic_arn = aws_sns_topic.sns_process_errors.arn
  protocol  = "email"
  endpoint  = var.email
}

resource "aws_sns_topic_subscription" "user_receives_cleanup_errors" {
  topic_arn = aws_sns_topic.sns_cleanup_errors.arn
  protocol  = "email"
  endpoint  = var.email
}

# give lambda roles permission to write to SNS
#resource "aws_iam_role_policy_attachment" "attach_sns_process" {
#  role       = var.iam_role_lambda_process_name
#  policy_arn = aws_iam_policy.sns_topic_policy_process.arn
#}

#resource "aws_iam_role_policy_attachment" "attach_sns_clean" {
#  role       = var.iam_role_lambda_clean_name
#  policy_arn = aws_iam_policy.sns_topic_policy_cleanup.arn
#}

output "sns_cleanup_errors_arn" {
  value = aws_sns_topic.sns_cleanup_errors.arn
}

output "sns_process_errors_arn" {
  value = aws_sns_topic.sns_process_errors.arn
}