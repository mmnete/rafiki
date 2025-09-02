from app.tools.tool_registry import ToolRegistry, AccessLevel
from enum import Enum
from typing import List


class ToolAccessManager:
    """
    Manages which tools a user can access based on their status
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
    
    def get_available_tools_for_user(self, user) -> List[str]:
        """Get list of tool names available to user"""
        if not user:
            return self._get_tools_for_access_level(AccessLevel.ALL)
        
        # Determine user's access level
        access_level = self._determine_user_access_level(user)
        
        # Get tools for this access level
        available_tools = []
        
        # Always include "all" level tools
        available_tools.extend(self._get_tools_for_access_level(AccessLevel.ALL))
        
        # Add level-specific tools
        if access_level in [AccessLevel.ONBOARDED, AccessLevel.TRUSTED_TESTER]:
            available_tools.extend(self._get_tools_for_access_level(AccessLevel.ONBOARDED))
        
        if access_level == AccessLevel.TRUSTED_TESTER:
            available_tools.extend(self._get_tools_for_access_level(AccessLevel.TRUSTED_TESTER))
        
        return list(set(available_tools))  # Remove duplicates
    
    def _determine_user_access_level(self, user) -> AccessLevel:
        """Determine user's access level"""
        if getattr(user, 'is_trusted_tester', False):
            return AccessLevel.TRUSTED_TESTER
        elif self._is_user_onboarded(user):
            return AccessLevel.ONBOARDED
        else:
            return AccessLevel.ALL
    
    def _is_user_onboarded(self, user) -> bool:
        """Check if user is fully onboarded"""
        if not user:
            return False
        
        required_fields = ['first_name', 'last_name', 'location', 'preferred_language']
        return all(getattr(user, field, None) for field in required_fields)
    
    def _get_tools_for_access_level(self, access_level: AccessLevel) -> List[str]:
        """Get tool names for specific access level"""
        return [
            name for name, tool_def in self.tool_registry.tools.items()
            if tool_def.access_level == access_level
        ]
    
    def can_user_access_tool(self, user, tool_name: str) -> bool:
        """Check if user can access specific tool"""
        available_tools = self.get_available_tools_for_user(user)
        return tool_name in available_tools
