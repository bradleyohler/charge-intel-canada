variable "snowflake_organization_name" {
  description = "Snowflake organization name (the part before the dash in orgname-accountname)"
  type        = string
}

variable "snowflake_account_name" {
  description = "Snowflake account name (the part after the dash in orgname-accountname)"
  type        = string
}

variable "snowflake_admin_user" {
  description = "Snowflake admin username used for Terraform provisioning"
  type        = string
}

variable "snowflake_private_key_path" {
  description = "Path to the PEM-encoded private key file (.p8) for key-pair authentication"
  type        = string
  default     = "terraform_svc_key.p8"
}

variable "snowflake_region" {
  description = "Snowflake account region (e.g. us-east-1)"
  type        = string
  default     = ""
}
