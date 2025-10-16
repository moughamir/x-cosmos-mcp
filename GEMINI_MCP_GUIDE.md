# Using Gemini CLI with Your MCP Application

## Introduction

This guide will walk you through using the Gemini CLI to interact with your Model Context Protocol (MCP) application. Since Gemini CLI can execute shell commands, you can use tools like `curl` to communicate with your application's API.

## Prerequisites

Before you begin, ensure your MCP application is running. You can start it with the following command:

```bash
docker compose up -d
```

## Using `curl` with Gemini CLI

You can ask Gemini to execute `curl` commands to interact with your MCP application's API. Gemini will execute the command and show you the output.

## API Interaction Examples

Here are some examples of how you can use `curl` within Gemini CLI to interact with your MCP application.

### 1. Get All Products

To get a list of all products, you can use the following command:

```bash
curl http://localhost:8000/api/products
```

### 2. Get Product Details

To get detailed information about a specific product, you'll need the product's ID. For example, to get details for product with ID `172840065`:

```bash
curl http://localhost:8000/api/products/172840065
```

### 3. Update a Product

To update a product, you'll need the product's ID and the data you want to update. For example, to update the title and description of product `172840065`:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "title": "New Updated Product Title",
    "body_html": "This is the new updated product description."
  }' \
  http://localhost:8000/api/products/172840065/update
```

### 4. Get Available Ollama Models

To see a list of all available Ollama models in your application:

```bash
curl http://localhost:8000/api/ollama/models
```

### 5. Pull a New Ollama Model

To download a new Ollama model, you can send a POST request with the model name. For example, to pull the `llama3.2:1b` model:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"model_name": "llama3.2:1b"}' \
  http://localhost:8000/api/ollama/pull
```

## Conclusion

As you can see, you can easily interact with your MCP application's API through the Gemini CLI by using `curl` or other command-line tools. This allows you to integrate your application into your workflow within the CLI.
