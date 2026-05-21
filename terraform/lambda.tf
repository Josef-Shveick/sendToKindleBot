locals {
  secrets = jsondecode(file("${path.module}/../secrets.json")).Variables
}

resource "aws_lambda_function" "kindlebot" {
  function_name = "SendToKindleBot"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.kindlebot.repository_url}@${var.image_digest}"
  memory_size   = 512
  timeout       = 30
  architectures = ["x86_64"]

  environment {
    variables = local.secrets
  }

  lifecycle {
    ignore_changes = [
      reserved_concurrent_executions,
    ]
  }
}
