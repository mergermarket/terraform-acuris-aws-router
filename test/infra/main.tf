# configure provider to not try too hard talking to AWS API
provider "aws" {
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_get_ec2_platforms      = true
  skip_region_validation      = true
  skip_requesting_account_id  = true
  max_retries                 = 1
  access_key                  = "a"
  secret_key                  = "a"
  region                      = "eu-west-1"
}

module "router" {
  source = "../.."

  alb_domain      = "${var.alb_domain}"
  team            = "${var.team}"
  env             = "${var.env}"
  component       = "${var.component}"
  platform_config = "${var.platform_config}"
}

# variables

variable "alb_domain" {}

variable "team" {}

variable "env" {}

variable "component" {}

variable "platform_config" {
  type = "map"
}
