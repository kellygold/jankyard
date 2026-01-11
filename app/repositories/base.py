"""Base repository pattern for database operations"""
from typing import Generic, TypeVar, Type, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def get(self, id: int) -> Optional[ModelType]:
        """Get a single record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Any = None
    ) -> List[ModelType]:
        """Get multiple records with pagination"""
        query = self.db.query(self.model)
        if order_by is not None:
            query = query.order_by(order_by)
        return query.offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**kwargs)
        self.db.add(db_obj)
        # Don't flush - causes hangs. SQLAlchemy will auto-flush when needed.
        return db_obj
    
    def update(self, db_obj: ModelType, **kwargs) -> ModelType:
        """Update an existing record"""
        for key, value in kwargs.items():
            setattr(db_obj, key, value)
        # Don't flush - SQLAlchemy will auto-flush when needed
        return db_obj
    
    def delete(self, id: int) -> bool:
        """Delete a record by ID"""
        db_obj = self.get(id)
        if db_obj:
            self.db.delete(db_obj)
            # Don't flush - SQLAlchemy will auto-flush when needed
            return True
        return False
    
    def count(self) -> int:
        """Count total records"""
        return self.db.query(self.model).count()
    
    def commit(self):
        """Commit the transaction"""
        self.db.commit()
    
    def rollback(self):
        """Rollback the transaction"""
        self.db.rollback()
    
    def refresh(self, db_obj: ModelType) -> ModelType:
        """Refresh an object from database"""
        self.db.refresh(db_obj)
        return db_obj
