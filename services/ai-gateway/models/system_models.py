# services/ai-gateway/models/system_models.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class FileSearchRequest(BaseModel):
    query: str
    directory: Optional[str] = None
    file_types: List[str] = []
    content_search: bool = False
    use_semantic: bool = True

class SystemMetricsRequest(BaseModel):
    metrics: List[str] = ["cpu", "memory", "disk", "processes"]
    duration: Optional[int] = None

class ProcessInfo(BaseModel):
    pid: int
    name: str
    cpu: float
    memory: float
    command: str

class SystemMetricsResponse(BaseModel):
    timestamp: str
    metrics: Dict[str, Any]
