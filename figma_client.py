import httpx
import os
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import json

load_dotenv()

class FigmaClient:
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("FIGMA_ACCESS_TOKEN")
        self.base_url = "https://api.figma.com/v1"
        self.headers = {
            "X-Figma-Token": self.access_token,
            "Content-Type": "application/json"
        }
    
    async def get_file(self, file_key: str) -> Dict[str, Any]:
        """Fetch Figma file data"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/files/{file_key}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    def extract_text_nodes(self, node: Dict[str, Any], parent_screen: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recursively extract text nodes from Figma file structure.

        Hidden layers (``visible`` == False) are ignored entirely so they will not
        surface in the API responses.
        """

        # Skip any node (and its subtree) that is not visible in Figma
        if node.get("visible", True) is False:
            return []

        text_nodes = []
        
        # Check if current node is a text node
        if node.get("type") == "TEXT":
            text_data = {
                "name": node.get("name", ""),
                "content": self._extract_text_content(node),
                "axis_x": node.get("absoluteBoundingBox", {}).get("x", 0),
                "axis_y": node.get("absoluteBoundingBox", {}).get("y", 0),
                "screen": parent_screen
            }
            text_nodes.append(text_data)
        
        # Check if current node is a frame (potential screen)
        if node.get("type") == "FRAME":
            current_screen = node.get("name", parent_screen)
            # Process children with current frame as screen context
            for child in node.get("children", []):
                text_nodes.extend(self.extract_text_nodes(child, current_screen))
        else:
            # For other node types, continue with existing screen context
            for child in node.get("children", []):
                text_nodes.extend(self.extract_text_nodes(child, parent_screen))
        
        return text_nodes
    
    def _extract_text_content(self, text_node: Dict[str, Any]) -> str:
        """Extract text content from text node"""
        characters = text_node.get("characters", "")
        return characters
    
    def organize_by_pages_and_screens(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Organize extracted data by Pages -> Screens -> Texts"""
        organized_data = {}
        
        document = file_data.get("document", {})
        pages = document.get("children", [])
        
        for page in pages:
            if page.get("type") != "CANVAS":
                continue
                
            page_name = page.get("name", "Unnamed Page")
            page_id = page.get("id", "")
            
            organized_data[page_name] = {
                "page_id": page_id,
                "screens": {}
            }
            
            # Get top-level frames (screens)
            screens = [child for child in page.get("children", []) if child.get("type") == "FRAME"]
            
            for screen in screens:
                screen_name = screen.get("name", "Unnamed Screen")
                screen_id = screen.get("id", "")
                
                # Extract all visible text nodes from this screen
                text_nodes = self.extract_text_nodes(screen, screen_name)

                # Skip screens that end up with no visible texts
                if not text_nodes:
                    continue

                organized_data[page_name]["screens"][screen_name] = {
                    "screen_id": screen_id,
                    "texts": text_nodes
                }
        
        return organized_data
    
    async def get_organized_text_data(self, file_key: str) -> Dict[str, Any]:
        """Main method to get organized text data from Figma file"""
        file_data = await self.get_file(file_key)
        return self.organize_by_pages_and_screens(file_data)
    
 