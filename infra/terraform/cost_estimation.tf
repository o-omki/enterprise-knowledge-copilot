output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown (USD)"
  value = {
    gke_autopilot     = "~$74/mo (0.5 vCPU × $31 + 2 GB × $3.4 × 6 pods)"
    cloud_sql         = var.environment == "staging" ? "~$8/mo (db-f1-micro, single zone)" : "~$60/mo (db-custom-2-4096, HA)"
    artifact_registry = "~$0.10/GB stored"
    secret_manager    = "~$0.24/mo (4 secrets × 10K accesses)"
    cloud_nat         = "~$1.50/mo"
    total_staging     = "~$85–100/mo"
    total_prod        = "~$180–250/mo (higher replicas + db tier)"
  }
}

check "cost_guard_db_tier" {
  assert {
    condition     = var.environment == "prod" || var.db_tier == "db-f1-micro"
    error_message = "WARNING: Non-prod environments should use db-f1-micro to minimize costs."
  }
}
