import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def _create_json_error_response(
    status_code: int, message: str, error_type: str, details: Any = None
) -> JSONResponse:
    content = {"message": message, "code": status_code, "error_type": error_type}
    if details:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content)


async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.status_code} - {exc.detail}", exc_info=True)
    return _create_json_error_response(exc.status_code, exc.detail, "HTTPException")


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()}", exc_info=True)
    return _create_json_error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Validation error",
        "RequestValidationError",
        exc.errors(),
    )


async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return _create_json_error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Internal server error",
        "InternalServerError",
    )
