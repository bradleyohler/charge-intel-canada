terraform {
  required_version = ">= 1.7"

  required_providers {
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.90"
    }
  }

  # Local backend for scaffold; swap to remote (S3/Terraform Cloud) for production
  backend "local" {}
}

provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = var.snowflake_admin_user
  private_key       = file(var.snowflake_private_key_path)
  authenticator     = "JWT"
}
