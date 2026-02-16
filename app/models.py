from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    projects = relationship("Project", back_populates="owner")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    user_id = Column(Integer, ForeignKey("users.id"))
    enable_telegram = Column(Boolean, default=True)
    enable_vk = Column(Boolean, default=True)
    owner = relationship("User", back_populates="projects")
    content_items = relationship("ContentItem", back_populates="project")

class ContentItem(Base):
    __tablename__ = "content_items"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String, nullable=False)
    text = Column(Text, default="")
    status = Column(String, default="draft")
    image_style = Column(String, default="")
    image_count = Column(Integer, default=1)
    images = Column(JSON().with_variant(SQLiteJSON, "sqlite"), default=[])
    project = relationship("Project", back_populates="content_items")

class ErrorLog(Base):
    __tablename__ = "error_logs"
    id = Column(Integer, primary_key=True, index=True)
    content_item_id = Column(Integer)
    module = Column(String)
    error = Column(Text)
    severity = Column(String)
    created_at = Column(String)
