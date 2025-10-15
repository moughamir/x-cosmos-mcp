import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkerStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class WorkerTask:
    task_id: str
    task_type: str
    data: Any
    priority: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class WorkerResult:
    task_id: str
    success: bool
    result: Any = None
    error: str = None
    execution_time: float = 0
