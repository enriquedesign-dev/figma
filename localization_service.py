import re
import json
import hmac
import hashlib
import base64
from datetime import datetime
from typing import Dict, Any, Optional
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from sync_service import SyncService

def sanitize_key(name: str, separator: str = "_") -> str:
    """
    Sanitizes a string to be a valid localization key.
    - Converts to lowercase
    - Replaces unsupported characters and sequences of them with a single separator
    - Removes leading/trailing separators
    """
    # Replace any non-alphanumeric characters with a separator
    name = re.sub(r'[^a-zA-Z0-9]+', separator, name)
    # Convert to lowercase and strip leading/trailing separators
    return name.lower().strip(separator)

class LocalizationService:
    def __init__(self, sync_service: SyncService):
        self.sync_service = sync_service
        self.hmac_secret = os.getenv("HMAC_SECRET_KEY", "").encode('utf-8')

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generates a Base64 encoded HMAC-SHA256 signature."""
        if not self.hmac_secret:
            return ""
        
        # Create a canonical JSON string to ensure consistent signature
        canonical_json = json.dumps(data, separators=(',', ':'), sort_keys=True).encode('utf-8')
        
        # Generate HMAC-SHA256
        signature = hmac.new(self.hmac_secret, canonical_json, hashlib.sha256).digest()
        
        # Return as Base64 encoded string
        return base64.b64encode(signature).decode('utf-8')

    async def generate_json_output(self, file_key: str, page_name_query: str) -> Optional[Dict[str, Any]]:
        """
        Generates a structured JSON file for a specific page,
        suitable for custom localization systems.
        """
        data = await self.sync_service.get_stored_data(file_key)
        if not data or not data["pages"]:
            return None

        strings = {}
        target_page = None
        key_counts = {}

        # Find the correct page (case-insensitive)
        for p_name, p_data in data["pages"].items():
            if p_name.lower() == page_name_query.lower():
                target_page = p_data
                break
        
        if not target_page:
            return None

        # Sort screens by their top-most text's Y-axis
        sorted_screens = sorted(
            target_page["screens"].items(),
            key=lambda item: min((float(t["axis_y"]) for t in item[1]["texts"]), default=0)
        )

        for screen_name, screen_data in sorted_screens:
            sanitized_screen_name = sanitize_key(screen_name, separator=".")
            
            # Sort texts by Y-axis to ensure consistent order
            sorted_texts = sorted(screen_data["texts"], key=lambda x: float(x["axis_y"]))

            for text_data in sorted_texts:
                sanitized_text_name = sanitize_key(text_data["name"], separator=".")
                base_key = f"{sanitized_screen_name}.{sanitized_text_name}"

                current_count = key_counts.get(base_key, 0)
                key_counts[base_key] = current_count + 1

                if current_count > 0:
                    # Append suffix for duplicates. Using `_` is safer than `.`
                    final_key = f"{base_key}_{current_count}"
                else:
                    final_key = base_key

                strings[final_key] = text_data["content"]

        version = int(data["last_updated"].timestamp()) if data.get("last_updated") else int(datetime.utcnow().timestamp())
        
        output = {
            "version": version,
            "strings": strings,
        }
        
        # Generate signature based on the final strings content
        output["signature"] = self._generate_signature(output["strings"])
        
        return output

    async def generate_xml_output(self, file_key: str, page_name_query: str) -> Optional[str]:
        """
        Generates an Android-compatible strings.xml file for a specific page.
        """
        data = await self.sync_service.get_stored_data(file_key)
        if not data or not data["pages"]:
            return None

        target_page = None
        # Find the correct page (case-insensitive)
        for p_name, p_data in data["pages"].items():
            if p_name.lower() == page_name_query.lower():
                target_page = p_data
                break

        if not target_page:
            return None

        root = Element('resources')
        key_counts = {}

        # Sort screens and texts to ensure consistent output file
        sorted_screens = sorted(
            target_page["screens"].items(),
            key=lambda item: min((float(t["axis_y"]) for t in item[1]["texts"]), default=0)
        )

        for screen_name, screen_data in sorted_screens:
            sanitized_screen_name = sanitize_key(screen_name)
            
            sorted_texts = sorted(screen_data["texts"], key=lambda x: float(x["axis_y"]))

            for text_data in sorted_texts:
                sanitized_text_name = sanitize_key(text_data["name"])
                base_key = f"{sanitized_screen_name}_{sanitized_text_name}"
                
                current_count = key_counts.get(base_key, 0)
                key_counts[base_key] = current_count + 1

                if current_count > 0:
                    final_key = f"{base_key}_{current_count}"
                else:
                    final_key = base_key

                # Create the <string> element
                child = SubElement(root, 'string', name=final_key)
                child.text = text_data["content"]

        # Pretty print the XML
        rough_string = tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="    ") 