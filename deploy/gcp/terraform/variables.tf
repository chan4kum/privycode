variable "project_id" {
  type        = string
  description = "The Google Cloud Platform project ID."
  default     = "sovereignforge-prod"
}

variable "region" {
  type        = string
  description = "The GCP region to deploy resources into."
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Deployment environment (production, staging, dev)."
  default     = "prod"
}

variable "db_instance_tier" {
  type        = string
  description = "Cloud SQL machine tier."
  default     = "db-custom-4-16384"
}
