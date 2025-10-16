# Project Tech Stack

This document outlines the key technologies and frameworks used in this project.

## Backend

*   **Programming Language:** Python
*   **Package/Environment Management:** The project uses a standard Python `venv` for dependency isolation. `uv` is utilized as a fast, modern Python package installer and resolver.
*   **API Framework:** FastAPI provides the high-performance web framework for building the API.
*   **Databases:**
    *   **Primary:** PostgreSQL serves as the robust, primary database for production environments.
    *   **Development/Local:** SQLite is used for lightweight, local development and testing.
*   **AI/ML:** Ollama is integrated for running and managing local large language models.
*   **Real-time Communication:** FastAPI WebSockets enable real-time, two-way communication between the server and clients.

## Frontend

*   **Framework:** Next.js is the React framework used for building the server-rendered and static frontend application.
*   **Package Manager:** PNPM is used for managing Node.js packages, as indicated by the `pnpm-lock.yaml` file.

## DevOps & Infrastructure

*   **Containerization:** Docker is used to create consistent, isolated environments for the application components.
*   **Orchestration:** Docker Compose manages the multi-container setup, defining and running the interconnected services (backend, database, etc.).
*   **Version Control:** Git is the version control system for tracking changes in the codebase.
