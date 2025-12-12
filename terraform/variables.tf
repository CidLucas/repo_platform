variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "vizudev"
}

variable "gcp_region" {
  description = "GCP Region"
  type        = string
  default     = "southamerica-east1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "docker_registry" {
  description = "Docker registry URL"
  type        = string
  default     = "us-east1-docker.pkg.dev/vizudev/vizu-mono"
}
