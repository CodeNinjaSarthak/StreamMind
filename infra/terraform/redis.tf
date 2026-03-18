# Redis infrastructure

variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# TODO: Add actual Redis resource definitions
# resource "aws_elasticache_cluster" "redis" {
#   cluster_id = "streammind-redis"
#   engine     = "redis"
#   node_type  = var.redis_node_type
# }

