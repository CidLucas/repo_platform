terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  required_version = ">= 1.0"
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# VPC Network
resource "google_compute_network" "vizu_vpc" {
  name                    = "vizu-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

# Subnets
resource "google_compute_subnetwork" "agents_subnet" {
  name          = "agents-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.gcp_region
  network       = google_compute_network.vizu_vpc.id
}

resource "google_compute_subnetwork" "workers_subnet" {
  name          = "workers-subnet"
  ip_cidr_range = "10.0.2.0/24"
  region        = var.gcp_region
  network       = google_compute_network.vizu_vpc.id
}

resource "google_compute_subnetwork" "dashboard_subnet" {
  name          = "dashboard-subnet"
  ip_cidr_range = "10.0.3.0/24"
  region        = var.gcp_region
  network       = google_compute_network.vizu_vpc.id
}

resource "google_compute_subnetwork" "redis_subnet" {
  name          = "redis-subnet"
  ip_cidr_range = "10.0.4.0/24"
  region        = var.gcp_region
  network       = google_compute_network.vizu_vpc.id
}

# Firewall Rules
resource "google_compute_firewall" "allow_internal" {
  name    = "allow-internal"
  network = google_compute_network.vizu_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  source_ranges = [
    "10.0.0.0/16"
  ]
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh"
  network = google_compute_network.vizu_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_firewall" "allow_http_https" {
  name    = "allow-http-https"
  network = google_compute_network.vizu_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
}

# Service Account
resource "google_service_account" "vizu_sa" {
  account_id   = "vizu-deployment"
  display_name = "Vizu Deployment Service Account"
}

# IAM Roles for Service Account
resource "google_project_iam_member" "artifact_registry_reader" {
  project = var.gcp_project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.vizu_sa.email}"
}

resource "google_project_iam_member" "secret_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.vizu_sa.email}"
}

# Static IPs
resource "google_compute_address" "agents_ip" {
  name   = "vizu-agents-ip"
  region = var.gcp_region
}

resource "google_compute_address" "workers_ip" {
  name   = "vizu-workers-ip"
  region = var.gcp_region
}

resource "google_compute_address" "dashboard_ip" {
  name   = "vizu-dashboard-ip"
  region = var.gcp_region
}

resource "google_compute_address" "redis_ip" {
  name   = "vizu-redis-ip"
  region = var.gcp_region
}

# Agents Pool VM
resource "google_compute_instance" "agents_pool" {
  name         = "vizu-agents-pool"
  machine_type = "e2-standard-4"
  zone         = "${var.gcp_region}-a"

  boot_disk {
    initialize_params {
      image = "ubuntu-2204-lts"
      size  = 50
    }
  }

  network_interface {
    network            = google_compute_network.vizu_vpc.name
    subnetwork         = google_compute_subnetwork.agents_subnet.name
    network_ip         = "10.0.1.10"

    access_config {
      nat_ip = google_compute_address.agents_ip.address
    }
  }

  service_account {
    email  = google_service_account.vizu_sa.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = file("${path.module}/startup-agents.sh")

  tags = ["http-server", "https-server", "agents-pool"]
}

# Workers Pool VM
resource "google_compute_instance" "workers_pool" {
  name         = "vizu-workers-pool"
  machine_type = "e2-standard-4"
  zone         = "${var.gcp_region}-b"

  boot_disk {
    initialize_params {
      image = "ubuntu-2204-lts"
      size  = 50
    }
  }

  network_interface {
    network            = google_compute_network.vizu_vpc.name
    subnetwork         = google_compute_subnetwork.workers_subnet.name
    network_ip         = "10.0.2.10"

    access_config {
      nat_ip = google_compute_address.workers_ip.address
    }
  }

  service_account {
    email  = google_service_account.vizu_sa.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = file("${path.module}/startup-workers.sh")

  tags = ["http-server", "https-server", "workers-pool"]
}

# Dashboard VM
resource "google_compute_instance" "dashboard" {
  name         = "vizu-dashboard"
  machine_type = "e2-standard-2"
  zone         = "${var.gcp_region}-c"

  boot_disk {
    initialize_params {
      image = "ubuntu-2204-lts"
      size  = 30
    }
  }

  network_interface {
    network            = google_compute_network.vizu_vpc.name
    subnetwork         = google_compute_subnetwork.dashboard_subnet.name
    network_ip         = "10.0.3.10"

    access_config {
      nat_ip = google_compute_address.dashboard_ip.address
    }
  }

  service_account {
    email  = google_service_account.vizu_sa.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = file("${path.module}/startup-dashboard.sh")

  tags = ["http-server", "https-server", "dashboard"]
}

# Redis VM
resource "google_compute_instance" "redis" {
  name         = "vizu-redis"
  machine_type = "e2-standard-2"
  zone         = "${var.gcp_region}-a"

  boot_disk {
    initialize_params {
      image = "ubuntu-2204-lts"
      size  = 50
    }
  }

  network_interface {
    network            = google_compute_network.vizu_vpc.name
    subnetwork         = google_compute_subnetwork.redis_subnet.name
    network_ip         = "10.0.4.10"

    access_config {
      nat_ip = google_compute_address.redis_ip.address
    }
  }

  service_account {
    email  = google_service_account.vizu_sa.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = file("${path.module}/startup-redis.sh")

  tags = ["redis", "internal"]
}

# Outputs
output "agents_ip" {
  value       = google_compute_address.agents_ip.address
  description = "Public IP of Agents Pool VM"
}

output "workers_ip" {
  value       = google_compute_address.workers_ip.address
  description = "Public IP of Workers Pool VM"
}

output "dashboard_ip" {
  value       = google_compute_address.dashboard_ip.address
  description = "Public IP of Dashboard VM"
}

output "redis_ip" {
  value       = google_compute_address.redis_ip.address
  description = "Public IP of Redis VM"
}

output "redis_internal_ip" {
  value       = google_compute_instance.redis.network_interface[0].network_ip
  description = "Internal IP of Redis VM for internal VPC access"
}
