import json
import logging
from typing import List, Dict, Any, AsyncGenerator
from datetime import datetime
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """OpenAI-compatible LLM service with streaming and tool calling"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the AI"""
        current_date = datetime.now().strftime("%B %d, %Y")
        current_time = datetime.now().strftime("%H:%M:%S")
        return f"""You are a helpful, knowledgeable AI assistant. The current date is {current_date} and the current time is {current_time}. You have access to internal tools to help answer questions.

When you need to get user information or system metrics, use the available tools. Be conversational and helpful.
Always provide clear, concise responses."""
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Define available tools/functions for the LLM"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "fetch_user_profile",
                    "description": "Fetch user profile information including name, email, and account status",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "The user ID to fetch profile for"
                            }
                        },
                        "required": ["user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_metrics",
                    "description": "Get current system metrics including CPU, memory, and response time",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "metric_type": {
                                "type": "string",
                                "enum": ["cpu", "memory", "all"],
                                "description": "Type of metric to retrieve"
                            }
                        },
                        "required": ["metric_type"]
                    }
                }
            }
        ]
    
    async def stream_response(
        self, 
        conversation: List[Dict[str, str]],
        use_tools: bool = True
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response with optional tool calling"""
        
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ] + conversation
        
        tools = self.get_tools() if use_tools else None
        
        try:
            # Initial streaming call
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tools=tools,
                tool_choice="auto" if use_tools else None,
                stream=True
            )
            
            full_response = ""
            tool_calls = []
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
                
                # Collect tool calls if present
                if chunk.choices[0].delta.tool_calls:
                    tool_calls.extend(chunk.choices[0].delta.tool_calls)
            
            # Handle tool calling if needed
            if tool_calls and use_tools:
                logger.info(f"Tool calls detected: {len(tool_calls)}")
                yield "\n\n[Processing tool request...]\n"
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in tool_calls
                    ]
                })
                
                # Process each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_result = await self._execute_tool(tool_name, tool_args)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })
                
                # Get follow-up response after tool execution
                follow_up_stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True
                )
                
                async for chunk in follow_up_stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"Error in stream_response: {e}")
            yield f"\n\nError: {str(e)}"
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result"""
        logger.info(f"Executing tool: {tool_name} with args: {args}")
        
        if tool_name == "fetch_user_profile":
            # Simulated user profile
            return {
                "user_id": args.get("user_id", "unknown"),
                "name": "John Doe",
                "email": "john.doe@example.com",
                "account_status": "active",
                "created_at": "2024-01-15",
                "subscription_tier": "premium"
            }
        
        elif tool_name == "get_system_metrics":
            # Simulated system metrics
            return {
                "metric_type": args.get("metric_type", "all"),
                "cpu_usage": 45.2,
                "memory_usage": 62.8,
                "response_time_ms": 125,
                "uptime_hours": 48,
                "timestamp": "2024-12-17T00:00:00Z"
            }
        
        return {"error": f"Unknown tool: {tool_name}"}


llm_service = LLMService()
