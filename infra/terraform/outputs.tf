output "vpc_id" {
  value = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "Public URL for the application load balancer"
  value       = aws_lb.app.dns_name
}

output "rds_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  sensitive = true
}

output "ecr_repository_urls" {
  value = { for name, repo in aws_ecr_repository.services : name => repo.repository_url }
}

output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.order_notification.function_name
}

output "app_instance_public_ip" {
  value = aws_instance.k3s_node.public_ip
}
