Router terraform module
================================

[![Build Status](https://travis-ci.org/mergermarket/tf_router.svg?branch=master)](https://travis-ci.org/mergermarket/tf_router)

This modules creates components needed to be able to expose your application(s) to the public, but does not include Fastly configuration.

When included and configured this module will:
- create public ALB
- create a HTTPS Listener on default ALB with default target group
- output default target group ARN

The final product is an AWS ALB which you can configure your services to be attached.

Module Input Variables
----------------------

See `/variables.tf`.

Usage
-----
```hcl

# the below platform_config map can be passed as a TF var-file (eg. JSON file)
variable "platform_config" {
  type = "map"
  default  = {
    platform_config: {
      azs: "eu-west-1a,eu-west-1b,eu-west-1c",
      elb_certificates.domain_com: "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012",
      route53_zone_id.domain_com: "AAAAAAAAAAAAA",
      ecs_cluster.default.client_security_group: "sg-00000000",
      ecs_cluster.default.security_group: "sg-11111111",
      vpc: "vpc-12345678",
      public_subnets: "subnet-00000000,subnet-11111111,subnet-22222222",
      logentries_fastly_logset_id: "111-222-333-444-555"
    }
  }
}

module "router" {
  source = "github.com/mergermarket/tf_router"

  alb_domain      = "domain.com"
  env             = "ci"
  component       = "wall"
  platform_config = "${var.platform_config}"
}
```

Outputs
-------

See `/outputs.tf`.
