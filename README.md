\# UCE Trámites - Monorepo (QA)



\## 1) Setup (requisitos)

\- Windows + PowerShell

\- Docker Desktop (WSL2 recomendado)

\- Git (opcional, para clonar)



\## 2) Run QA (levantar todo con Docker Compose)

Desde la raíz del repo:



```powershell

docker compose -f docker\\docker-compose.local.yml up -d --build

docker ps



\## Servicios y puertos (QA)

\- auth-service: http://localhost:8001

\- tramites-service: http://localhost:8002

\- documents-service: http://localhost:8003

\- rabbitmq management: http://localhost:15672

\- kafka: localhost:9092

\- postgres: localhost:5432

\- redis: localhost:6379



\## Swagger / Docs

\- auth-service: http://localhost:8001/docs

\- tramites-service: http://localhost:8002/docs

\- documents-service: http://localhost:8003/docs



> Entorno QA local levantado con Docker Compose (`docker/docker-compose.local.yml`).



