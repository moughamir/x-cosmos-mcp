import uvicorn
from app.utils.logging_config import setup_logging

from app.api import app

if __name__ == "__main__":
    setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8080)
