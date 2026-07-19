import {
  to = google_secret_manager_secret.gemini_api_key
  id = "projects/${var.project_id}/secrets/ekc-gemini-api-key"
}

import {
  to = google_secret_manager_secret.jwt_secret_key
  id = "projects/${var.project_id}/secrets/ekc-jwt-secret-key"
}

import {
  to = google_secret_manager_secret.postgres_password
  id = "projects/${var.project_id}/secrets/ekc-postgres-password"
}

import {
  to = google_secret_manager_secret.default_api_key
  id = "projects/${var.project_id}/secrets/ekc-default-api-key"
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id  = "ekc-gemini-api-key"
  project    = var.project_id
  depends_on = [google_project_service.apis]

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret" "jwt_secret_key" {
  secret_id  = "ekc-jwt-secret-key"
  project    = var.project_id
  depends_on = [google_project_service.apis]

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret" "postgres_password" {
  secret_id  = "ekc-postgres-password"
  project    = var.project_id
  depends_on = [google_project_service.apis]

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_secret_manager_secret_version" "postgres_password_version" {
  secret      = google_secret_manager_secret.postgres_password.id
  secret_data = random_password.postgres_password.result
}

resource "google_secret_manager_secret" "default_api_key" {
  secret_id  = "ekc-default-api-key"
  project    = var.project_id
  depends_on = [google_project_service.apis]

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Grant Application SA permission to read these secrets
resource "google_secret_manager_secret_iam_member" "app_accessor_gemini" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "app_accessor_jwt" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.jwt_secret_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "app_accessor_postgres" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.postgres_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "app_accessor_default_key" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.default_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}
