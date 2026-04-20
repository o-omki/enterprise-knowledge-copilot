# ADR 0005: Cloud Provider Choice

## Status
Accepted

## Context
The project needs a reliable infrastructure for hosting the application services (FastAPI), vector database (Qdrant), and metadata database (PostgreSQL), along with Kubernetes for orchestration.

## Decision
We will use **Google Cloud Platform (GCP)** as the primary cloud provider.

## Rationale
- **GKE (Google Kubernetes Engine):** Industry-leading managed Kubernetes service with excellent scaling and management features.
- **AI Ecosystem:** Strong integration possibilities with Vertex AI for future model serving optimizations or monitoring.
- **Infrastructure:** Robust networking and storage options (Cloud Storage, Cloud SQL if needed) that fit the architecture.
- **User Preference:** Explicitly requested by the user.

## Alternatives Considered
- **Azure:** Strong for enterprise but GCP was selected by preference.
- **AWS:** Industry giant, but GKE often provides a more streamlined managed k8s experience.

## Consequences
- Infrastructure as Code (Terraform) will target GCP resources (`google` provider).
- Deployment scripts and CI will need `gcloud` CLI and service account configurations.
