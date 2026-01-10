\# UCE Trámites - Monorepo (QA)



## 1) Requisitos
- Windows + PowerShell
- Docker Desktop (WSL2 recomendado)
- Git



## 2) Levantar entorno QA (Docker Compose)
```bash
docker compose -f docker/docker-compose.local.yml up -d --build
docker ps


Para detener:
docker compose -f docker/docker-compose.local.yml down



## Servicios y puertos (QA)
 
-auth-service: http://localhost:8001

-tramites-service: http://localhost:8002

-documents-service: http://localhost:8003

-notifications-service: http://localhost:8004

-rabbitmq management: http://localhost:15672

-kafka: localhost:9092

-postgres: localhost:5432

-redis: localhost:6379

***Swagger / Docs: ****

-auth-service: http://localhost:8001/docs

 feature/readme-qa
\- prueba: localhost:6379

-tramites-service: http://localhost:8002/docs
-qa

-documents-service: http://localhost:8003/docs

-notifications-service: http://localhost:8004/docs


**Pruebas rápidas (end-to-end)*
 
-Crear tramites
Invoke-RestMethod -Method Post -Uri "http://localhost:8003/documents" -ContentType "application/json" -Body '{"tramite_id":1,"nombre":"certificado.pdf","url":"https://example.com/certificado.pdf"}'

-Subir documentos 

Invoke-RestMethod -Method Post -Uri "http://localhost:8002/tramites" -ContentType "application/json" -Body '{"estudiante_id":"1720000000","tipo":"certificado_matricula"}'


* ver logs *
docker logs -f notifications_service



