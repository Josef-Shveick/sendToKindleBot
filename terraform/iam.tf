resource "aws_iam_role" "lambda_exec" {
  name = "SendToKindleBot-role-d8s48g7z"
  path = "/service-role/"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/service-role/AWSLambdaBasicExecutionRole-52777376-e28d-4ab7-8344-9a7886348773"
}
