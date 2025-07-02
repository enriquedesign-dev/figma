from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class TextData(BaseModel):
    name: str
    content: str
    axis_x: float
    axis_y: float

class ScreenData(BaseModel):
    screen_id: str
    texts: List[TextData]

class PageData(BaseModel):
    page_id: str
    screens: Dict[str, ScreenData]

class FigmaDataResponse(BaseModel):
    pages: Dict[str, PageData]
    last_updated: datetime
    figma_file_key: str

class SyncResponse(BaseModel):
    success: bool
    message: str
    pages_updated: int
    texts_updated: int
    last_sync: datetime

class HealthResponse(BaseModel):
    status: str
    database_connected: bool
    figma_api_configured: bool 