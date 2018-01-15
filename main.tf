module "default_backend_ecs_service" {
  source = "modules/deprecated"

  name   = "${replace(replace(format("%s-%s", var.env, var.component), "/(.{0,24}).*/", "$1"), "/^-+|-+$/", "")}-default"
  vpc_id = "${var.platform_config["vpc"]}"
}

locals {
  desired_load_balancer_name = "${var.env}-${var.component}" 
  abbreviated_load_balancer_name = "${
    join("", list(
      substr(
        local.desired_load_balancer_name, 0,
        length(local.desired_load_balancer_name) >= 24 ?
          24 : length(local.desired_load_balancer_name)
      ),
      substr(sha1(local.desired_load_balancer_name), 0, 8)
    ))
  }"
}

module "alb" {
  source = "github.com/mergermarket/tf_alb.git"

  name                     = "${
    length(local.desired_load_balancer_name) > 32 ?
      local.abbreviated_load_balancer_name :
      local.desired_load_balancer_name
  }"
  vpc_id                   = "${var.platform_config["vpc"]}"
  subnet_ids               = ["${split(",", var.platform_config["public_subnets"])}"]
  extra_security_groups    = ["${var.platform_config["ecs_cluster.default.client_security_group"]}"]
  internal                 = "false"
  certificate_domain_name  = "${format("*.%s%s", var.env != "live" ? "dev." : "", var.alb_domain)}"
  default_target_group_arn = "${aws_alb_target_group.default_target_group.arn}"
  access_logs_bucket       = "${lookup(var.platform_config, "elb_access_logs_bucket", "")}"
  access_logs_enabled      = "${"${lookup(var.platform_config, "elb_access_logs_bucket", "")}" == "" ? false : true}"

  tags = {
    component   = "${var.component}"
    environment = "${var.env}"
    team        = "${var.team}"
  }
}

locals {
  desired_default_target_group_name = "${var.env}-default-${var.component}" 
  abbreviated_default_target_group_name = "${
    join("", list(
      substr(
        local.desired_default_target_group_name, 0,
        length(local.desired_default_target_group_name) >= 24 ?
          24 : length(local.desired_default_target_group_name)
      ),
      substr(sha1(local.desired_default_target_group_name), 0, 8)
    ))
  }"
}

resource "aws_alb_target_group" "default_target_group" {
  name = "${
    length(local.desired_default_target_group_name) > 32 ?
      local.abbreviated_default_target_group_name :
      local.desired_default_target_group_name
  }"

  # port will be set dynamically, but for some reason AWS requires a value
  port                 = "31337"
  protocol             = "HTTP"
  vpc_id               = "${var.platform_config["vpc"]}"
  deregistration_delay = "${var.default_target_group_deregistration_delay}"

  health_check {
    interval            = "${var.default_target_group_health_check_interval}"
    path                = "${var.default_target_group_health_check_path}"
    timeout             = "${var.default_target_group_health_check_timeout}"
    healthy_threshold   = "${var.default_target_group_health_check_healthy_threshold}"
    unhealthy_threshold = "${var.default_target_group_health_check_unhealthy_threshold}"
    matcher             = "${var.default_target_group_health_check_matcher}"
  }
}

module "dns_record" {
  source = "github.com/mergermarket/tf_route53_dns"

  domain      = "${var.alb_domain}"
  name        = "${var.component}"
  env         = "${var.env}"
  target      = "${module.alb.alb_dns_name}"
  alb_zone_id = "${module.alb.alb_zone_id}"
  alias       = "1"
}
