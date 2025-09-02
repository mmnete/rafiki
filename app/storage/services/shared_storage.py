from app.services.redis_storage_manager import implemented_redis_storage_manager
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class SharedStorageService:
    """Service for caching search results and temporary data"""
    
    def __init__(self):
        self.redis_manager = implemented_redis_storage_manager
    
    def cache_search_results(self, user_id: int, search_params: Dict[str, Any], 
                           results: Any, ttl_minutes: int = 30) -> str:
        """Cache flight search results"""
        # Generate search ID
        search_id = self._generate_search_id(user_id, search_params)
        
        # Cache data
        cache_data = {
            'search_params': search_params,
            'results': results,
            'cached_at': datetime.now().isoformat(),
            'user_id': user_id
        }
        
        # Store with TTL
        self.redis_manager.set_data(
            f"search:{user_id}:{search_id}", 
            cache_data, 
            ttl=ttl_minutes * 60
        )
        
        return search_id
    
    def get_cached_search(self, user_id: int, search_id: str) -> Optional[Dict[str, Any]]:
        """Get cached search results"""
        return self.redis_manager.get_data(f"search:{user_id}:{search_id}")
    
    def _generate_search_id(self, user_id: int, search_params: Dict[str, Any]) -> str:
        """Generate unique search ID"""
        import hashlib
        import time
        
        # Create hash from params + timestamp for uniqueness
        params_str = json.dumps(search_params, sort_keys=True)
        timestamp = str(int(time.time()))
        hash_input = f"{user_id}:{params_str}:{timestamp}"
        
        search_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return f"search_{search_hash}"

# Global instance
shared_storage_service = SharedStorageService()