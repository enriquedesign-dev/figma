#!/usr/bin/env python3
"""
Standalone synchronization script to fetch data from Figma and update the database.
Can be run manually or via cron job for automated syncing.
"""

import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

from figma_client import FigmaClient
from sync_service import SyncService
from database import create_tables

load_dotenv()

async def main():
    """Main sync function"""
    figma_token = os.getenv("FIGMA_ACCESS_TOKEN")
    figma_file_key = os.getenv("FIGMA_FILE_KEY")
    
    if not figma_token:
        print("Error: FIGMA_ACCESS_TOKEN environment variable not set")
        sys.exit(1)
    
    if not figma_file_key:
        print("Error: FIGMA_FILE_KEY environment variable not set")
        sys.exit(1)
    
    print(f"Starting sync at {datetime.now()}")
    print(f"Figma File Key: {figma_file_key}")
    
    try:
        # Initialize database
        await create_tables()
        print("✓ Database initialized")
        
        # Initialize services
        figma_client = FigmaClient(figma_token)
        sync_service = SyncService(figma_client)
        
        # Perform sync
        print("Fetching data from Figma...")
        result = await sync_service.sync_figma_data(figma_file_key)
        
        if result["success"]:
            print("✓ Sync completed successfully!")
            print(f"  - Pages updated: {result['pages_updated']}")
            print(f"  - Texts updated: {result['texts_updated']}")
            print(f"  - Last sync: {result['last_sync']}")
        else:
            print(f"✗ Sync failed: {result['message']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Error during sync: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 