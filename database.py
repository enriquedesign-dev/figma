from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./mobile_app_data.db")

# Async engine for SQLite
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class FigmaPage(Base):
    __tablename__ = "figma_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String, unique=True, index=True)
    page_name = Column(String, index=True)
    figma_file_key = Column(String, index=True)
    json_data = Column(Text)  # Store complete JSON structure
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class FigmaText(Base):
    __tablename__ = "figma_texts"
    
    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String, index=True)
    screen_id = Column(String, index=True)
    screen_name = Column(String, index=True)
    text_name = Column(String, index=True)
    text_content = Column(Text)
    axis_x = Column(Float)
    axis_y = Column(Float)
    figma_file_key = Column(String, index=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) 