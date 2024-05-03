variable "token" {
  type = string
}

resource "aws_ssm_parameter" "token" {
  name        = var.token
  value       = ""
  type        = "SecureString"
  description = "My token"
}

output "secret_arn" {
  value = aws_ssm_parameter.token.arn
}