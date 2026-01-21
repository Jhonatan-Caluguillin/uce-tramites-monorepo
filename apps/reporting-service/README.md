\# reporting-service



Microservicio de reportes/KPIs para el monorepo \*\*uce-tramites\*\*.

Expone endpoints HTTP para consultar métricas consolidadas desde PostgreSQL (y opcionalmente puede ampliarse a eventos Kafka).



\## Stack

\- FastAPI + Uvicorn

\- PostgreSQL (lectura de tablas del dominio)

\- Docker + Docker Compose

\- NX (targets docker-build / docker-up)



\## Variables de entorno (local)

| Variable | Ejemplo | Descripción |

|---|---|---|

| DB\_HOST | postgres | Host de PostgreSQL (service name en compose) |

| DB\_PORT | 5432 | Puerto |

| DB\_NAME | uce\_tramites | Base |

| DB\_USER | uce | Usuario |

| DB\_PASS | uce123 | Password |

| KAFKA\_BOOTSTRAP | kafka:9092 | (Opcional) Broker Kafka |



\## Levantar con Docker (monorepo)

\### Opción A: NX

```bash

.\\nx run reporting-service:docker-build

.\\nx run reporting-service:docker-up



