from fastmcp import FastMCP

from app.api import app

# Generate the MCP server from the FastAPI app
mcp = FastMCP.from_fastapi(app=app)

if __name__ == "__main__":
    mcp.run()
