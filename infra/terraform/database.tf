resource "google_sql_database_instance" "postgres" {
  name             = "ekc-db-${var.environment}"
  database_version = "POSTGRES_16"
  region           = var.region
  project          = var.project_id

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.apis
  ]

  settings {
    tier = var.db_tier

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
    }

    user_labels = {
      environment = var.environment
      project     = "enterprise-knowledge-copilot"
      managed-by  = "terraform"
    }
  }

  deletion_protection = var.enable_deletion_protection

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_sql_database" "knowledge_copilot" {
  name     = "knowledge_copilot"
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

resource "google_sql_user" "db_user" {
  name     = "knowledge_copilot_user"
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
  password = random_password.postgres_password.result
}

resource "random_password" "postgres_password" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}
