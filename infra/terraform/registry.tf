resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "ekc-images"
  description   = "Docker repository for Enterprise Knowledge Copilot images"
  format        = "DOCKER"
  project       = var.project_id
  depends_on    = [google_project_service.apis]

  # FinOps lifecycle cleanup policies
  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state = "UNTAGGED"
    }
  }
}

resource "google_artifact_registry_repository_iam_member" "gke_pull" {
  project    = var.project_id
  location   = google_artifact_registry_repository.docker_repo.location
  repository = google_artifact_registry_repository.docker_repo.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.gke_node_sa.email}"
}
