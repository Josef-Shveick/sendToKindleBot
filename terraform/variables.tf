variable "aws_region" {
  description = "aws region to use"
  type        = string
  default     = "eu-north-1"
}

variable "image_digest" {
  description = "ECR image digest (sha256:...) for the Lambda container image. Supplied by CI from docker push output."
  type        = string
}
