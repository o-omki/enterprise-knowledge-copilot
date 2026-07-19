resource "google_container_cluster" "primary" {
  name             = var.gke_cluster_name
  location         = var.region
  project          = var.project_id
  enable_autopilot = true
  depends_on       = [google_project_service.apis]

  network    = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.subnet.id

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods"
    services_secondary_range_name = "gke-services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false # Keep control plane accessible but restricted via master authorized networks
  }

  node_config {
    service_account = google_service_account.gke_node_sa.email
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "Allow All Ingress to Control Plane (for setup/testing; restrict in production)"
    }
  }

  # Maintenance window: Saturday 02:00-06:00 UTC
  maintenance_policy {
    recurring_window {
      start_time = "2026-06-27T02:00:00Z"
      end_time   = "2026-06-27T06:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SA"
    }
  }

  release_channel {
    channel = "REGULAR"
  }

  resource_labels = {
    environment = var.environment
    project     = "enterprise-knowledge-copilot"
    managed-by  = "terraform"
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [node_config]
  }
}
