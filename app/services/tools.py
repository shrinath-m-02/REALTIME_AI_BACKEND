import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ToolsService:
    """Service for executing tools that LLM can call"""
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result"""
        logger.info(f"Executing tool: {tool_name}")
        
        if tool_name == "fetch_user_profile":
            return await self._fetch_user_profile(args)
        elif tool_name == "get_system_metrics":
            return await self._get_system_metrics(args)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def _fetch_user_profile(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch user profile (simulated)"""
        user_id = args.get("user_id", "unknown")
        
        # Simulated user profiles
        profiles = {
            "user1": {
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "account_status": "active",
                "subscription_tier": "premium",
                "created_at": "2023-06-15"
            },
            "user2": {
                "name": "Bob Smith",
                "email": "bob@example.com",
                "account_status": "active",
                "subscription_tier": "free",
                "created_at": "2024-01-20"
            }
        }
        
        if user_id in profiles:
            profile = profiles[user_id]
        else:
            profile = {
                "name": "User " + user_id[:8],
                "email": f"{user_id}@example.com",
                "account_status": "pending",
                "subscription_tier": "free",
                "created_at": "2024-01-01"
            }
        
        logger.info(f"✓ User profile fetched: {profile.get('name')}")
        return {
            "user_id": user_id,
            **profile
        }
    
    async def _get_system_metrics(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system metrics (simulated)"""
        import psutil
        import os
        
        metric_type = args.get("metric_type", "all")
        
        try:
            # Get real metrics if psutil is available
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            metrics = {
                "cpu_usage_percent": cpu,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available / (1024 ** 3),
                "timestamp": os.popen("date").read().strip()
            }
        except:
            # Fallback simulated metrics
            metrics = {
                "cpu_usage_percent": 42.5,
                "memory_usage_percent": 58.3,
                "memory_available_gb": 8.2,
                "timestamp": "2024-12-17 10:30:00"
            }
        
        if metric_type == "cpu":
            metrics = {"cpu_usage_percent": metrics["cpu_usage_percent"]}
        elif metric_type == "memory":
            metrics = {
                "memory_usage_percent": metrics["memory_usage_percent"],
                "memory_available_gb": metrics["memory_available_gb"]
            }
        
        logger.info(f"✓ System metrics retrieved")
        return metrics


tools_service = ToolsService()
