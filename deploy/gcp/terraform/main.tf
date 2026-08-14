# ==============================================================================
# SovereignForge & PrivyCode — Google Cloud Platform (GCP) Production Terraform
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.15"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Private VPC Network
resource "google_compute_network" "sovereign_vpc" {
  name                    = "${var.environment}-sovereignforge-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "sovereign_subnet" {
  name          = "${var.environment}-sovereignforge-subnet"
  ip_cidr_range = "10.0.0.0/20"
  region        = var.region
  network       = google_compute_network.sovereign_vpc.id

  private_ip_google_access = true
}

# 2. Private Service Access for Cloud SQL & Redis
resource "google_compute_global_address" "private_ip_alloc" {
  name          = "${var.environment}-private-ip-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.sovereign_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.sovereign_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
}

# 3. Cloud SQL PostgreSQL 16 (Private IP Only)
resource "random_password" "db_password" {
  length  = 24
  special = false
}

resource "google_sql_database_instance" "postgres" {
  name             = "${var.environment}-sovereignforge-pg16"
  database_version = "POSTGRES_16"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier              = var.db_instance_tier
    availability_type = "REGIONAL"
    disk_type         = "PD_SSD"
    disk_size         = 100
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.sovereign_vpc.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "sovereignforge_db" {
  name     = "sovereignforge"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "sovereign_admin" {
  name     = "sovereign_admin"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

# 4. GCP Memorystore for Redis 7 (Private IP)
resource "google_redis_instance" "redis_cache" {
  name               = "${var.environment}-sovereignforge-redis"
  tier               = "STANDARD_HA"
  memory_size_gb     = 5
  region             = var.region
  redis_version      = "REDIS_7_0"
  authorized_network = google_compute_network.sovereign_vpc.id

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

# 5. GCP Artifact Registry Container Repository
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "${var.environment}-sovereignforge"
  description   = "SovereignForge & PrivyCode Private Container Images"
  format        = "DOCKER"
}

# 6. GCP Secret Manager (Database Credentials)
resource "google_secret_manager_secret" "db_url_secret" {
  secret_id = "${var.environment}-database-url"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_url_version" {
  secret      = google_secret_manager_secret.db_url_secret.id
  secret_data = "postgresql+asyncpg://sovereign_admin:${random_password.db_password.result}@${google_sql_database_instance.postgres.private_ip_address}:5432/sovereignforge?ssl=require"
}

# 7. Serverless VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "vpc_connector" {
  name          = "${var.environment}-cr-conn"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.sovereign_vpc.name
}

# 8. Cloud Armor Security & DDoS WAF Policy
resource "google_compute_security_policy" "cloud_armor" {
  name = "${var.environment}-sovereignforge-armor"

  rule {
    action   = "rate_based_ban"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 1000
        interval_sec = 60
      }
      ban_duration_sec = 300
    }
    description = "Enterprise rate limiting: 1000 requests per minute per IP"
  }

  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }
}

# 9. Cloud Run Gateway Service
resource "google_cloud_run_v2_service" "gateway" {
  name     = "${var.environment}-sovereignforge-gateway"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 2
      max_instance_count = 10
    }

    vpc_access {
      connector = google_vpc_access_connector.vpc_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/gateway:1.0.0"

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.redis_cache.host}:${google_redis_instance.redis_cache.port}/0"
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url_secret.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}
