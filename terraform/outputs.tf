output "database_name" {
  description = "Name of the Snowflake database"
  value       = snowflake_database.charge_intel_canada.name
}

output "warehouse_name" {
  description = "Name of the Snowflake virtual warehouse"
  value       = snowflake_warehouse.charge_intel_wh.name
}

output "role_name" {
  description = "Name of the Snowflake role for the application"
  value       = snowflake_account_role.charge_intel_role.name
}

output "service_user" {
  description = "Snowflake service account username"
  value       = snowflake_user.charge_intel_svc.name
}
