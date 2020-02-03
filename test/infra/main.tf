terraform {
  required_version = ">= 0.12"
}

provider "aws" {
  version                     = ">= 2.15"
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

  alb_domain = "domain.com"
  team       = "foobar"
  env        = "dev"
  component  = "foobar"
  platform_config = {
    "public_subnets" : "subnet-123479de3,subnet-123479de3"
    "vpc" : "vpc-id"
    "ecs_cluster.default.client_security_group" : "sg-id"
  }
  run_data = false
  zone_id  = "TESTZONEID"
}
