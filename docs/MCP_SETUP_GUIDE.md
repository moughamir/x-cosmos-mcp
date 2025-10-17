# MCP Setup Guide for Your Project

## Introduction

This guide will walk you through creating and setting up a Model Context Protocol (MCP) server for your project. We will use `fastmcp`, a Python library for building MCP servers, and integrate it with the Gemini CLI.

This will allow you to create custom tools to interact with your PostgreSQL database directly from Gemini.

## 1. Installation

First, you need to ensure that you have `fastmcp` installed.

```bash
# Install fastmcp
pip install fastmcp>=2.12.3
```

## 2. Creating Your MCP Server

Create a new file named `mcp_server.py` in the root of your project. This file will contain the logic for your MCP server and its tools.

Here is an example of a simple server that connects to your PostgreSQL database and provides a tool to list products:

```python
import os
import psycopg2
from fastmcp import MCP, tool

# Initialize the MCP server
mcp = MCP()

@tool()
def list_products(limit: int = 10):
    """Lists products from the database."""
    conn = None
    try:
        # Connect to your PostgreSQL database
        # It's recommended to use environment variables for connection details
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            dbname=os.environ.get("DB_NAME", "your_db_name"),
            user=os.environ.get("DB_USER", "your_db_user"),
            password=os.environ.get("DB_PASSWORD", "your_db_password")
        )
        cur = conn.cursor()
        cur.execute(f"SELECT id, title FROM products LIMIT {limit}")
        products = cur.fetchall()
        cur.close()
        return products
    except (Exception, psycopg2.DatabaseError) as error:
        return f"Error: {error}"
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    mcp.run()

```

**Important:**

*   You will need to set the environment variables (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) with your database connection details.
*   This example provides a simple `list_products` tool. You can create more tools to perform other database operations.

## 3. Installing the MCP Server in Gemini CLI

Now that you have your `mcp_server.py` file, you can install it into the Gemini CLI using the following command:

```bash
fastmcp install gemini-cli mcp_server.py
```

This command will make the tools defined in your `mcp_server.py` available within Gemini.

## 4. Using Your MCP Server in Gemini

Once the server is installed, you can use the tools you've defined directly in Gemini. For example, you can ask:

> "list the first 5 products"

Gemini will understand this and use your `list_products` tool to fetch the data from your database and provide you with the result.

You can also see the available tools by typing `/` and looking for the tools from your MCP server.

## Conclusion

By following this guide, you have created a powerful integration between Gemini and your project's database. You can now extend your `mcp_server.py` with more tools to create a rich, interactive experience for managing your application's data directly from Gemini.
