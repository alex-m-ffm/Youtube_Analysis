# new let's create an Amazon Eventbridge scheduler to call the functions based on a cron-job
variable "account_id" {
  type = string
}

variable "lambda_clean_arn" {
  type = string
}

variable "lambda_process_arn" {
  type = string
}

resource "aws_iam_role" "lambda_scheduler_role" {
  name        = "LambdaScheduling"
  description = "IAM role for Eventbridge scheduler to execute Lambda functions"

  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "scheduler.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": var.account_id
                }
            }
        }
    ]
})

}

resource "aws_iam_policy" "schedule_lambdas" {
  name        = "schedule-lambdas"
  description = "Policy for allowing the execution of our lambda functions"

  policy      = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [var.lambda_process_arn, var.lambda_clean_arn]
        }
    ]
})
}

resource "aws_iam_role_policy_attachment" "attach_lambda_access_scheduler_role" {
  role       = aws_iam_role.lambda_scheduler_role.name
  policy_arn = aws_iam_policy.schedule_lambdas.arn
}

resource "aws_scheduler_schedule" "daily_process_schedule" {
  name = "daily-processing"

  flexible_time_window {
    mode = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  schedule_expression = "cron(0 1 ? * * *)"
  schedule_expression_timezone = "US/Pacific"

  target {
    arn      = var.lambda_process_arn
    role_arn = aws_iam_role.lambda_scheduler_role.arn

    input = jsonencode({
      MessageBody = "Greetings, programs!"
    })
  }
}

# and the monthly cleanup

resource "aws_scheduler_schedule" "monthly_cleanup_schedule" {
  name = "monthly-cleaning"

  flexible_time_window {
    mode = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  schedule_expression = "cron(0 1 1 * ? *)"
  schedule_expression_timezone = "US/Pacific"

  target {
    arn      = var.lambda_clean_arn
    role_arn = aws_iam_role.lambda_scheduler_role.arn

    input = jsonencode({
      MessageBody = "Greetings, programs!"
    })
  }
}