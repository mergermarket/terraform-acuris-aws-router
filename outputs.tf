output "default_target_group_arn" {
  value = aws_alb_target_group.default_target_group.arn
}

output "dns_name" {
  value = module.dns_record.fqdn
}

output "alb_listener_arn" {
  value = module.alb.alb_listener_arn
}

