# Database infrastructure

variable "db_instance_class" {
  description = "Database instance class"
  type        = string
  default     = "db.t3.micro"
}

# TODO: Add actual database resource definitions
# resource "aws_db_instance" "main" {
#   identifier = "streammind-db"
#   engine     = "postgres"
#   instance_class = var.db_instance_class
# }

