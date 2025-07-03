import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.sqlite import insert
import os

from database import AsyncSessionLocal, FigmaPage, FigmaText
from figma_client import FigmaClient

class SyncService:
    def __init__(self, figma_client: FigmaClient):
        self.figma_client = figma_client
    
    async def sync_figma_data(self, file_key: str, debug: bool = False) -> Dict[str, Any]:
        """Main sync function to fetch and store Figma data."""
        try:
            # Fetch organized text data from Figma UI file
            organized_data = await self.figma_client.get_organized_text_data(file_key)
            pages_updated, texts_updated = await self._store_data(file_key, organized_data)

            debug_info: Dict[str, Any] | None = None

            # Generate debug details if requested
            if debug:
                debug_info = {
                    "page_names": list(organized_data.keys()),
                    "pages_updated": pages_updated,
                    "texts_updated": texts_updated,
                }

            return {
                "success": True,
                "message": "Data synchronized successfully",
                "pages_updated": pages_updated,
                "texts_updated": texts_updated,
                "last_sync": datetime.utcnow(),
                "debug_info": debug_info,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}",
                "pages_updated": 0,
                "texts_updated": 0,
                "last_sync": datetime.utcnow(),
                "debug_info": None,
            }
    
    async def _store_data(self, file_key: str, organized_data: Dict[str, Any]) -> tuple[int, int]:
        """Store organized data in database"""
        async with AsyncSessionLocal() as session:
            pages_count = 0
            texts_count = 0
            
            # Clear existing data for this file
            await session.execute(delete(FigmaText).where(FigmaText.figma_file_key == file_key))
            await session.execute(delete(FigmaPage).where(FigmaPage.figma_file_key == file_key))
            
            for page_name, page_data in organized_data.items():
                # Store page data
                page_record = FigmaPage(
                    page_id=page_data["page_id"],
                    page_name=page_name,
                    figma_file_key=file_key,
                    json_data=json.dumps(page_data),
                    last_updated=datetime.utcnow()
                )
                session.add(page_record)
                pages_count += 1
                
                # Store text data
                for screen_name, screen_data in page_data["screens"].items():
                    for text_data in screen_data["texts"]:
                        text_record = FigmaText(
                            page_id=page_data["page_id"],
                            screen_id=screen_data["screen_id"],
                            screen_name=screen_name,
                            text_name=text_data["name"],
                            text_content=text_data["content"],
                            axis_x=text_data["axis_x"],
                            axis_y=text_data["axis_y"],
                            figma_file_key=file_key,
                            last_updated=datetime.utcnow()
                        )
                        session.add(text_record)
                        texts_count += 1
            
            await session.commit()
            return pages_count, texts_count
    
    async def get_stored_data(self, file_key: str) -> Dict[str, Any]:
        """Retrieve stored data from database"""
        async with AsyncSessionLocal() as session:
            # Get pages
            result = await session.execute(
                select(FigmaPage).where(FigmaPage.figma_file_key == file_key)
            )
            pages = result.scalars().all()
            
            if not pages:
                return {"pages": {}, "last_updated": None, "figma_file_key": file_key}
            
            organized_data = {"pages": {}}
            latest_update = None
            
            for page in pages:
                page_data = json.loads(page.json_data)
                organized_data["pages"][page.page_name] = {
                    "page_id": page.page_id,
                    "screens": page_data["screens"]
                }
                
                if latest_update is None or page.last_updated > latest_update:
                    latest_update = page.last_updated
            
            return {
                "pages": organized_data["pages"],
                "last_updated": latest_update,
                "figma_file_key": file_key
            }

 