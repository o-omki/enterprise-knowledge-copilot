# Deployment Guide

## Goal
Deploy the knowledge copilot as a production-like multi-service application.

## Deployment Targets
- local development with Docker Compose
- cloud deployment for demo/staging
- Kubernetes-based deployment for production-style presentation

## Services
- API service
- worker/ingestion service
- vector database
- metadata database
- model serving backend
- frontend service
- monitoring stack

## Environments
### Local
Used for development and debugging.

### Staging
Used for integration testing and demos.

### Production-Style
Used to showcase scalable deployment patterns.

## Deployment Phases
1. local Docker Compose
2. managed cloud deployment for API/UI
3. Kubernetes rollout
4. monitoring and alerting integration

## Requirements
- containerized services
- environment-specific configs
- secret management
- health checks
- readiness/liveness probes
- rollback instructions

## Success Criteria
- a new developer can run the stack locally
- staging can be deployed reproducibly
- core services are observable after deployment