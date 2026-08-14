output "gateway_uri" {
  value       = google_cloud_run_v2_service.gateway.uri
  description = "The public endpoint URL of the SovereignForge API Gateway."
}

output "cloud_sql_private_ip" {
  value       = google_sql_database_instance.postgres.private_ip_address
  description = "Private IP of the PostgreSQL 16 database."
}

output "redis_host" {
  value       = google_redis_instance.redis_cache.host
  description = "Private IP host of Memorystore for Redis."
}

output "artifact_registry_url" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}"
  description = "Artifact Registry container image repository."
}
