\# NER-RESQ Backend API Documentation



\## Base URL



http://127.0.0.1:8000



\## Authentication



All protected endpoints require:



Authorization: Bearer <access\_token>



\---



\## Authentication



\### POST /api/auth/register



Register a new user.



\### POST /api/auth/login



Login and receive JWT access token.



\### GET /api/auth/me



Get the currently authenticated user.



\---



\## Dashboard



\### GET /api/dashboard



Roles:

\- ADMIN

\- OPERATOR



Returns vehicle, trip, incident and risk statistics.



\---



\## Vehicles



\### GET /api/vehicles



Get vehicles visible to the authenticated user.



\### PATCH /api/vehicles/{vehicle\_id}/gps



Update vehicle GPS information.



\### GET /api/vehicles/{vehicle\_id}



Get vehicle details.



\### GET /api/vehicles/{vehicle\_id}/monitor



Monitor vehicle status.



\---



\## Trips



\### GET /api/trips



Get trips.



\### GET /api/trips/{trip\_id}



Get one trip.



\### POST /api/trips



Create a trip.



\### POST /api/trips/{trip\_id}/start



Start a planned trip.



\### POST /api/trips/{trip\_id}/complete



Complete an active trip.



\### POST /api/trips/{trip\_id}/cancel



Cancel a trip.



\### POST /api/trips/{trip\_id}/reroute



Calculate a new route using ML routing.



\### GET /api/trips/{trip\_id}/monitor



Monitor route adherence and detect deviation.



\---



\## Route Planning



\### POST /api/routes/plan



Generate a recommended logistics route.



\---



\## Incidents



\### GET /api/incidents



List incidents.



\### GET /api/incidents/{incident\_id}



Get incident details.



\### GET /api/incidents/{incident\_id}/impact



Calculate affected trips.



\### POST /api/incidents/{incident\_id}/reroute



Reroute affected trips.



\### POST /api/incidents/{incident\_id}/resolve



Resolve an incident.



\---



\## Locations



\### GET /api/locations



List locations.



\### GET /api/locations/search



Search locations.



\---



\## Alerts



\### GET /api/alerts



Get active logistics alerts.



\---



\## Weather



\### GET /api/weather



Get weather information.



\---



\## Health



\### GET /health



Returns backend health status.



\---



\## Roles



ADMIN:

\- Full administrative access.



OPERATOR:

\- Logistics operations and monitoring.



DRIVER:

\- Access only to resources assigned to the driver.



\---



\## Development



Start backend:



uvicorn app.main:app --reload



Swagger:



http://127.0.0.1:8000/docs



Run tests:



pytest -v

