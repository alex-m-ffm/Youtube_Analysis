variable "token" {
  type = string
}

resource "aws_secretsmanager_secret" "token" {
  name = var.token
}

output "secret_arn" {
  value = aws_secretsmanager_secret.token.arn
}