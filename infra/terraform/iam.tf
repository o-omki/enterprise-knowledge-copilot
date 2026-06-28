# Custom GKE Node Service Account
resource "google_service_account" "gke_node_sa" {
  account_id   = "ekc-gke-node-sa"
  display_name = "GKE Node Service Account"
  project      = var.project_id
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "node_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.gke_node_sa.email}"
}

resource "google_project_iam_member" "node_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.gke_node_sa.email}"
}

resource "google_service_account" "app_sa" {
  account_id   = "ekc-app-sa"
  display_name = "EKC Application Service Account"
  project      = var.project_id
  depends_on   = [google_project_service.apis]
}

resource "google_service_account_iam_binding" "workload_identity_binding" {
  service_account_id = google_service_account.app_sa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[ekc-staging/ekc-workload-sa]",
    "serviceAccount:${var.project_id}.svc.id.goog[ekc-prod/ekc-workload-sa]",
    "serviceAccount:${var.project_id}.svc.id.goog[ekc-staging/staging-ekc-workload-sa]",
    "serviceAccount:${var.project_id}.svc.id.goog[ekc-prod/prod-ekc-workload-sa]"
  ]
}
