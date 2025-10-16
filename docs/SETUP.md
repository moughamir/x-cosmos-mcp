# Setup

This document describes how to set up the MCP Admin application.

## Prerequisites

- Python 3.11+
- Poetry
- Docker
- pnpm

## Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/moughamir/mcp-openai.git
    cd mcp-openai
    ```

2.  Install Python dependencies:

    ```bash
    poetry install
    ```

3.  Install frontend dependencies:

    ```bash
    cd frontend
    pnpm install
    cd ..
    ```

## Configuration

1.  Create a `.env` file from the example:

    ```bash
    cp .env.example .env
    ```

2.  Update the `.env` file with your database credentials.

3.  Update the `config.yaml` file to configure the models and other settings.

## Running the Application

### Using Docker

The recommended way to run the application is with Docker Compose.

1.  Build and start the containers:

    ```bash
    docker-compose up --build
    ```

2.  The application will be available at [http://localhost:8000](http://localhost:8000).

### Locally

You can also run the application locally for development.

1.  Start the backend server:

    ```bash
    poetry run uvicorn app.main:app --reload
    ```

2.  Start the frontend server:

    ```bash
    cd frontend
    pnpm dev
    ```

3.  The application will be available at [http://localhost:3000](http://localhost:3000).
