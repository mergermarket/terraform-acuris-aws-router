output "default_target_group_arn" {
  value = "${module.aws_alb_target_group.default_target_group.arn}"
}
