from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from collections import OrderedDict
import os
from dotenv import load_dotenv
from typing import Dict, List

from database import create_tables, get_db
from figma_client import FigmaClient
from sync_service import SyncService
from schemas import FigmaDataResponse, SyncResponse, HealthResponse

load_dotenv()

# Initialize Figma client and sync service
figma_client = FigmaClient()
sync_service = SyncService(figma_client)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Figma Text API",
    description="API for serving mobile app text content from Figma designs",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        database_connected=True,  # We'll assume SQLite is always available
        figma_api_configured=bool(os.getenv("FIGMA_ACCESS_TOKEN"))
    )

# Specific routes must come before parameterized routes to avoid conflicts
@app.get("/api/figma/texts")
async def get_default_figma_texts():
    """Get all texts from the default Figma file (using FIGMA_FILE_KEY from environment)"""
    try:
        default_file_key = os.getenv("FIGMA_FILE_KEY")
        
        if not default_file_key:
            raise HTTPException(
                status_code=400, 
                detail="FIGMA_FILE_KEY environment variable not set"
            )
        
        if default_file_key in ["your_figma_file_key_here", "test_file_key_placeholder"]:
            raise HTTPException(
                status_code=400, 
                detail="Please set a real FIGMA_FILE_KEY in your .env file"
            )
        
        # Get data using the sync service
        data = await sync_service.get_stored_data(default_file_key)
        
        if not data.get("pages"):
            raise HTTPException(
                status_code=404, 
                detail="No data found for default Figma file. Try syncing first with POST /api/sync"
            )
        
        # Create nested structure: Page → Screen → Text Name (ordered by axis_y)
        nested_structure = {}
        total_texts = 0
        
        for page_name, page_data in data["pages"].items():
            nested_structure[page_name] = {}
            
            # Sort screens by their topmost text position (y-axis)
            sorted_screens = sorted(
                page_data["screens"].items(),
                key=lambda item: min(float(t["axis_y"]) for t in item[1]["texts"])
            )
            
            for screen_name, screen_data in sorted_screens:
                # Sort texts by axis_y (top to bottom) - lowest y values first (top of screen)
                sorted_texts = sorted(screen_data["texts"], key=lambda x: float(x["axis_y"]), reverse=False)
                
                # Create ordered object with numbered keys to maintain order
                screen_texts = {}
                text_name_counts = {}  # Track duplicate names within the same screen
                
                for i, text in enumerate(sorted_texts, 1):
                    base_text_name = text["name"]
                    
                    # Handle duplicate text names by appending a counter
                    if base_text_name in text_name_counts:
                        text_name_counts[base_text_name] += 1
                        text_name = f"{base_text_name}_{text_name_counts[base_text_name]}"
                    else:
                        text_name_counts[base_text_name] = 0
                        text_name = base_text_name
                    
                    # Use numbered key to maintain order
                    key = f"{i:02d}_{text_name}"
                    screen_texts[key] = {
                        "text_content": text["content"],
                        "axis_x": float(text["axis_x"]),
                        "axis_y": float(text["axis_y"]),
                        "page_id": page_data["page_id"],
                        "screen_id": screen_data["screen_id"]
                    }
                    total_texts += 1
                
                nested_structure[page_name][screen_name] = screen_texts
        
        # Convert datetime to string for JSON serialization
        last_updated_str = None
        if data.get("last_updated"):
            if hasattr(data["last_updated"], 'isoformat'):
                last_updated_str = data["last_updated"].isoformat()
            else:
                last_updated_str = str(data["last_updated"])
        
        return {
            "total_texts": total_texts,
            "pages": nested_structure,
            "last_updated": last_updated_str
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/figma/data", response_model=FigmaDataResponse)
async def get_figma_data():
    """Get complete structured data from the default Figma file"""
    try:
        default_file_key = os.getenv("FIGMA_FILE_KEY")
        
        if not default_file_key:
            raise HTTPException(
                status_code=400, 
                detail="FIGMA_FILE_KEY environment variable not set"
            )
        
        data = await sync_service.get_stored_data(default_file_key)
        
        if not data["pages"]:
            raise HTTPException(
                status_code=404, 
                detail=f"No data found for default Figma file. Try syncing first with POST /api/sync"
            )
        
        return FigmaDataResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync", response_model=SyncResponse)
async def sync_figma_file(background_tasks: BackgroundTasks, debug: bool = Query(False)):
    """Sync default Figma file data to database"""
    try:
        default_file_key = os.getenv("FIGMA_FILE_KEY")
        
        if not default_file_key:
            raise HTTPException(
                status_code=400, 
                detail="FIGMA_FILE_KEY environment variable not set"
            )
        
        # Run sync in background for faster response
        result = await sync_service.sync_figma_data(default_file_key, debug=debug)
        return SyncResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@app.get("/api/figma/pages")
async def get_pages():
    """Get list of pages from the default Figma file"""
    try:
        default_file_key = os.getenv("FIGMA_FILE_KEY")
        
        if not default_file_key:
            raise HTTPException(
                status_code=400, 
                detail="FIGMA_FILE_KEY environment variable not set"
            )
        
        data = await sync_service.get_stored_data(default_file_key)
        
        if not data["pages"]:
            raise HTTPException(
                status_code=404, 
                detail="No data found for default Figma file"
            )
        
        pages = [
            {"name": page_name, "page_id": page_data["page_id"]}
            for page_name, page_data in data["pages"].items()
        ]
        
        return {"pages": pages, "count": len(pages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/figma/pages/{page_name}")
async def get_page_data(page_name: str):
    """Get data for a specific page from the default Figma file"""
    try:
        default_file_key = os.getenv("FIGMA_FILE_KEY")
        
        if not default_file_key:
            raise HTTPException(
                status_code=400, 
                detail="FIGMA_FILE_KEY environment variable not set"
            )
        
        data = await sync_service.get_stored_data(default_file_key)
        
        if page_name not in data["pages"]:
            raise HTTPException(
                status_code=404, 
                detail=f"Page '{page_name}' not found in default Figma file"
            )
        
        # Convert datetime to string for JSON serialization
        last_updated_str = None
        if data.get("last_updated"):
            if hasattr(data["last_updated"], 'isoformat'):
                last_updated_str = data["last_updated"].isoformat()
            else:
                last_updated_str = str(data["last_updated"])
        
        # Sort screens by their topmost text position (y-axis)
        page_data = data["pages"][page_name].copy()
        sorted_screens = sorted(
            page_data["screens"].items(),
            key=lambda item: min(float(t["axis_y"]) for t in item[1]["texts"])
        )

        ordered_screens = {}
        for screen_name, screen_data in sorted_screens:
            # Sort texts inside each screen by y-axis
            screen_data["texts"] = sorted(screen_data["texts"], key=lambda x: float(x["axis_y"]))
            ordered_screens[screen_name] = screen_data

        page_data["screens"] = ordered_screens
        
        return {
            "page": page_data,
            "last_updated": last_updated_str
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/figma/pages/{page_name}/screens/{screen_name}")
async def get_screen_data(page_name: str, screen_name: str):
    """Get data for a specific screen from the default Figma file"""
    try:
        default_file_key = os.getenv("FIGMA_FILE_KEY")
        
        if not default_file_key:
            raise HTTPException(
                status_code=400, 
                detail="FIGMA_FILE_KEY environment variable not set"
            )
        
        data = await sync_service.get_stored_data(default_file_key)
        
        if page_name not in data["pages"]:
            raise HTTPException(
                status_code=404, 
                detail=f"Page '{page_name}' not found in default Figma file"
            )
        
        if screen_name not in data["pages"][page_name]["screens"]:
            raise HTTPException(
                status_code=404, 
                detail=f"Screen '{screen_name}' not found in page '{page_name}'"
            )
        
        # Convert datetime to string for JSON serialization
        last_updated_str = None
        if data.get("last_updated"):
            if hasattr(data["last_updated"], 'isoformat'):
                last_updated_str = data["last_updated"].isoformat()
            else:
                last_updated_str = str(data["last_updated"])
        
        # Sort texts by axis_y within the screen
        screen_data = data["pages"][page_name]["screens"][screen_name].copy()
        screen_data["texts"] = sorted(screen_data["texts"], key=lambda x: float(x["axis_y"]))
        
        return {
            "screen": screen_data,
            "last_updated": last_updated_str
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test")
async def test_simple():
    """Simple test endpoint"""
    return {"message": "Test endpoint working", "status": "ok"}

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port) 