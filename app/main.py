import uvicorn
from .api import app
from .utils.logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8080)
