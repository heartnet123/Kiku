<div align="center">

<img src="./frontend/static/kiku-icon.png" alt="Kiku Logo" width="128" />

# Kiku

*Enterprise AI Knowledge Platform & Vector Search RAG Workspace*

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen?style=flat-square)](#)
[![Python Version](https://img.shields.io/badge/Python->=3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Svelte](https://img.shields.io/badge/Svelte-5.56+-FF3E00?style=flat-square&logo=svelte&logoColor=white)](https://svelte.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-blue?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![LlamaIndex](https://img.shields.io/badge/LlamaIndex-0.10+-black?style=flat-square)](https://www.llamaindex.ai)

[Overview](#overview) • [Architecture](#architecture) • [Features](#features) • [Getting Started](#getting-started) • [API Reference](#api-reference) • [Testing](#testing)

</div>

---

Kiku is a high-performance, enterprise-grade AI knowledge platform and Retrieval-Augmented Generation (RAG) system. It combines multi-tenant workspace isolation, role-based access control (RBAC), document ingestion pipelines, and interactive search experiences powered by LlamaIndex, Supabase Vector Store, and Svelte 5.

> [!NOTE]
> Kiku is designed with strict data privacy in mind, featuring automatic PII redaction and audit logging across all workspace operations.

## Overview

Modern organizations face challenges organizing, indexing, and searching through internal documentation across isolated teams. Kiku solves this by providing a unified knowledge ingestion engine and search platform with strict tenant boundaries.

### Key Highlights

- **Multi-Tenant Workspaces**: Complete data isolation with workspace-scoped permissions and member management.
- **RAG & Knowledge Search**: Advanced document chunking, embedding generation, and vector retrieval using LlamaIndex and Supabase.
- **Modern Web Interface**: Responsive UI powered by Svelte 5 (Runes), Tailwind CSS v4, and Vite.
- **Enterprise Security**: Role-based access control (RBAC), JWT authentication, PII redaction, and audit trail events.

## Architecture

The project is structured as a monorepo consisting of a FastAPI backend service and a SvelteKit frontend web application.

```
kiku/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/v1/routes/    # Versioned HTTP API routers
│   │   ├── core/             # Auth, Security & PII Audit Logging
│   │   ├── domain/           # Domain models & Password hashing
│   │   ├── schemas/          # Pydantic request/response contracts
│   │   └── services/         # Ingestion pipeline, Vector search, Storage
│   ├── tests/                # Pytest unit & integration test suite
│   └── pyproject.toml        # Dependencies managed via `uv`
│
└── frontend/                 # SvelteKit 5 Web Application
    ├── src/
    │   ├── lib/              # Components, API clients, and stores
    │   └── routes/           # SvelteKit pages (Search, Sources, Settings)
    ├── static/               # Static assets & branding
    └── package.json          # Frontend dependencies
```

### Data Flow

```
[ PDF / MD Document ] ──► [ Ingestion Pipeline ] ──► [ Supabase Vector Store ]
                                                              │
[ User Query ] ─────────► [ Search Service ] ───────────────► [ Vector Search ] ──► [ RAG Response ]
```

> [!TIP]
> Document ingestion runs through LlamaIndex, generating nodes and OpenAI embeddings stored directly in Supabase vector tables.

## Features

- **Document Ingestion & Versioning**: Support for PDF and Markdown files with status tracking (`ready`, `indexing`, `failed`) and version history.
- **Intelligent Search**: Contextual search answers powered by vector similarity, complete with citations, page numbers, and related FAQs.
- **Workspace Access Control**: Granular roles (`Admin`, `Member`), invitation workflows, and membership management.
- **Security Audit Logs**: Track workspace changes, membership updates, and source modifications with automatic PII masking.
- **Ingestion Telemetry**: Pipeline monitoring providing metrics on node counts, memory usage, and ingestion latency.

## Getting Started

### Prerequisites

Ensure you have the following installed:

- **Python**: `>= 3.12`
- **Node.js**: `>= 20` (or **Bun** `>= 1.1`)
- **uv**: `pip install uv` or official `uv` installer

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Copy the example environment configuration:
   ```bash
   cp .env.example .env
   ```

3. Install dependencies and start the development server:
   ```bash
   uv run fastapi dev app/main.py
   ```

The backend server will run on `http://localhost:8000` with interactive API documentation available at `http://localhost:8000/docs`.

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Copy the example environment configuration:
   ```bash
   cp .env.example .env
   ```

3. Install dependencies and start the development server:
   ```bash
   bun install
   bun run dev
   ```

> [!IMPORTANT]
> Make sure `PUBLIC_API_BASE_URL` in `frontend/.env` points to your running backend (default: `http://localhost:8000`).

The frontend web app will be available at `http://localhost:5173`.

## API Reference

### Health & Auth

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/health` | `GET` | Service health status check |
| `/api/v1/auth/login` | `POST` | User authentication & JWT generation |
| `/api/v1/auth/me` | `GET` | Retrieve current user profile and accessible workspaces |

### Knowledge & Search

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/workspaces/{workspace_id}/search` | `POST` | Execute vector RAG search query with citations |
| `/api/v1/workspaces/{workspace_id}/sources` | `GET` | List knowledge sources and ingestion statuses |
| `/api/v1/workspaces/{workspace_id}/sources/upload` | `POST` | Upload PDF or Markdown document for ingestion |
| `/api/v1/workspaces/{workspace_id}/sources/{source_id}/retry` | `POST` | Retry failed ingestion job |
| `/api/v1/workspaces/{workspace_id}/sources/telemetry` | `GET` | Retrieve pipeline execution telemetry |

### Workspace Administration

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/workspaces/{workspace_id}/members` | `GET` | List members of a workspace |
| `/api/v1/workspaces/{workspace_id}/members/invite` | `POST` | Invite a user to the workspace |
| `/api/v1/workspaces/{workspace_id}/members/{user_id}` | `PATCH` | Update member role (`admin`, `member`) |
| `/api/v1/workspaces/{workspace_id}/members/{user_id}` | `DELETE` | Revoke workspace access |
| `/api/v1/workspaces/{workspace_id}/audit-logs` | `GET` | Retrieve audit events for the workspace |

## Testing

### Backend Tests

Run the Pytest suite for unit, integration, and security authorization checks:

```bash
cd backend
uv run pytest
```

### Frontend Tests

Run the Vitest suite for component and logic verification:

```bash
cd frontend
bun run test
```