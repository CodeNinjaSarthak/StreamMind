# API infrastructure

variable "api_instance_type" {
  description = "API instance type"
  type        = string
  default     = "t3.small"
}

# TODO: Add actual API resource definitions
# resource "aws_ecs_service" "api" {
#   name = "streammind-api"
# }

