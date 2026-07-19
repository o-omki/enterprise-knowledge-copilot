variable "project_id" {
  type        = string
  description = "The GCP project ID to deploy resources into"
  default     = "clean-carrier-500104-i0"
}

variable "region" {
  type        = string
  description = "The GCP region to deploy resources into"
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Deployment environment (staging or prod)"
  default     = "staging"

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "Environment must be either 'staging' or 'prod'."
  }
}

variable "db_tier" {
  type        = string
  description = "The database instance machine type tier"
  default     = "db-f1-micro"

  validation {
    condition     = contains(["db-f1-micro", "db-g1-small", "db-custom-2-4096"], var.db_tier)
    error_message = "db_tier must be one of: db-f1-micro, db-g1-small, db-custom-2-4096. Prevents accidental expensive tier."
  }
}

variable "gke_cluster_name" {
  type        = string
  description = "The name of the GKE cluster"
  default     = "ekc-cluster"
}

variable "enable_deletion_protection" {
  type        = bool
  description = "Whether deletion protection is enabled on the database"
  default     = true
}
