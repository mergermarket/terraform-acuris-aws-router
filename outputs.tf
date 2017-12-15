output "default_target_group_arn" {
  value = "${aws_alb_target_group.default_target_group.arn}"
}
