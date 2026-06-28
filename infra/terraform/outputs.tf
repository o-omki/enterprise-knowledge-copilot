output "gke_cluster_endpoint" {
  description = "GKE Autopilot cluster control plane endpoint"
  value       = google_container_cluster.primary.endpoint
}

output "gke_cluster_ca_certificate" {
  description = "GKE Autopilot cluster CA certificate"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "cloud_sql_private_ip" {
  description = "Cloud SQL instance private IP address"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "artifact_registry_url" {
  description = "Artifact Registry repository URL"
  value       = "${google_artifact_registry_repository.docker_repo.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}"
}

output "gke_node_sa_email" {
  description = "Email of custom GKE Node Service Account"
  value       = google_service_account.gke_node_sa.email
}

output "app_sa_email" {
  description = "Email of custom Workload Identity Application Service Account"
  value       = google_service_account.app_sa.email
}
