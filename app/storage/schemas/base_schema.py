from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSchema(ABC):
    """Base class for all database schemas"""
    
    def __init__(self):
        self.table_name = None
        self.version = "1.0.0"
    
    @abstractmethod
    def get_table_definitions(self) -> List[str]:
        """Return list of CREATE TABLE statements"""
        pass
    
    @abstractmethod
    def get_indexes(self) -> List[str]:
        """Return list of CREATE INDEX statements"""
        pass
    
    def get_migrations(self) -> List[str]:
        """Return list of ALTER TABLE statements for schema updates"""
        return []
    
    def validate_schema(self) -> bool:
        """Validate schema consistency"""
        return True
