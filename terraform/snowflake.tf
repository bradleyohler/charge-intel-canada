# Database
resource "snowflake_database" "charge_intel_canada" {
  name    = "CHARGE_INTEL_CANADA"
  comment = "ChargeIntel Canada – EV charging analytics"
}

# Schemas (medallion layers)
resource "snowflake_schema" "bronze" {
  database = snowflake_database.charge_intel_canada.name
  name     = "BRONZE"
  comment  = "Raw ingested data; no transformations"
}

resource "snowflake_schema" "silver" {
  database = snowflake_database.charge_intel_canada.name
  name     = "SILVER"
  comment  = "Cleaned and normalized tables"
}

resource "snowflake_schema" "gold" {
  database = snowflake_database.charge_intel_canada.name
  name     = "GOLD"
  comment  = "Analytics-ready aggregated tables"
}

# Virtual warehouse
resource "snowflake_warehouse" "charge_intel_wh" {
  name           = "CHARGE_INTEL_WH"
  warehouse_size = "XSMALL"
  auto_suspend   = 60
  auto_resume    = true
  comment        = "ChargeIntel workload warehouse"
}

# Application role
resource "snowflake_account_role" "charge_intel_role" {
  name    = "CHARGE_INTEL_ROLE"
  comment = "Role for the ChargeIntel service account"
}

# Service account user (key-pair auth; set rsa_public_key in Snowsight after apply)
resource "snowflake_user" "charge_intel_svc" {
  name              = "CHARGE_INTEL_SVC"
  default_warehouse = snowflake_warehouse.charge_intel_wh.name
  default_role      = snowflake_account_role.charge_intel_role.name
  comment           = "ChargeIntel Canada service account"
}

# Assign role to service user
resource "snowflake_grant_account_role" "charge_intel_svc_role" {
  role_name = snowflake_account_role.charge_intel_role.name
  user_name = snowflake_user.charge_intel_svc.name
}

# Warehouse – USAGE
resource "snowflake_grant_privileges_to_account_role" "warehouse_usage" {
  account_role_name = snowflake_account_role.charge_intel_role.name
  privileges        = ["USAGE"]
  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.charge_intel_wh.name
  }
}

# Database – USAGE, CREATE SCHEMA
resource "snowflake_grant_privileges_to_account_role" "database_usage" {
  account_role_name = snowflake_account_role.charge_intel_role.name
  privileges        = ["USAGE", "CREATE SCHEMA"]
  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.charge_intel_canada.name
  }
}

# Schema privileges – Bronze
resource "snowflake_grant_privileges_to_account_role" "bronze_schema" {
  account_role_name = snowflake_account_role.charge_intel_role.name
  privileges        = ["USAGE", "CREATE TABLE", "CREATE VIEW", "CREATE STAGE"]
  on_schema {
    schema_name = "\"${snowflake_database.charge_intel_canada.name}\".\"${snowflake_schema.bronze.name}\""
  }
}

# Schema privileges – Silver
resource "snowflake_grant_privileges_to_account_role" "silver_schema" {
  account_role_name = snowflake_account_role.charge_intel_role.name
  privileges        = ["USAGE", "CREATE TABLE", "CREATE VIEW", "CREATE STAGE"]
  on_schema {
    schema_name = "\"${snowflake_database.charge_intel_canada.name}\".\"${snowflake_schema.silver.name}\""
  }
}

# Schema privileges – Gold
resource "snowflake_grant_privileges_to_account_role" "gold_schema" {
  account_role_name = snowflake_account_role.charge_intel_role.name
  privileges        = ["USAGE", "CREATE TABLE", "CREATE VIEW", "CREATE STAGE"]
  on_schema {
    schema_name = "\"${snowflake_database.charge_intel_canada.name}\".\"${snowflake_schema.gold.name}\""
  }
}
