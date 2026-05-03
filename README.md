# Blood Routing CVRP

A project focused on modelling and solving a vehicle routing problem for Irish blood distribution.

The system is a web-based decision-support prototype. It allows a user to define routing scenarios, run optimisation jobs, and visualise resulting routes on a map.

## Project Overview

This project investigates routing methods for national medical supply distribution, with an initial focus on blood delivery between depots and hospitals in Ireland.

The practical artefact consists of:

- a Python backend for scenario handling and route computation
- a SvelteKit frontend for interaction and visualisation
- map-based route display using Leaflet
- comparison between custom heuristics and Google OR-Tools

## Current Technology Stack

Backend:
- Python 3.12
- FastAPI
- Google OR-Tools
- ProcessPoolExecutor for background solve jobs

Frontend:
- SvelteKit
- TypeScript
- Leaflet.js

Data:
- scraped Irish hospital dataset with coordinates retrieved from https://www.geohive.ie/datasets/feb34881088341bbbf80d86af6a4f333_0
- distance / travel-time / route geometries from OpenRoutingService API
- JSON file-based storage to persist scenarios, Solver Jobs, Solutions, and to cache external API responses

## Repository Structure

```text
blood-cvrp/
├─ .env
├─ .gitignore
├─ backend/
│  ├─ requirements.txt
│  ├─ seed/
│  │  ├─ Hospitals_-_HSE_Ireland.csv
│  │  ├─ ors_api_key.env
│  │  ├─ storage/
│  │  ├─ storage_seed.py
│  │  └─ __init__.py
│  └─ src/
│     ├─ api/
│     ├─ application/
│     ├─ data/
│     ├─ solver/
│     ├─ settings.py
│     └─ main.py
├─ docs/
├─ frontend/
│  ├─ .npmrc
│  ├─ eslint.config.js
│  ├─ node_modules/
│  ├─ package-lock.json
│  ├─ package.json
│  ├─ src/
│  ├─ static/
│  ├─ svelte.config.js
│  ├─ tsconfig.json
│  └─ vite.config.ts
├─ runs/
└─ README.md
```
