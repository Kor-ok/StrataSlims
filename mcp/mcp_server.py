#!/usr/bin/env python3
"""
StrataSlims MCP Server

This module provides Model Context Protocol (MCP) server functionality for StrataSlims,
a Discord bot for music generation using Suno AI.
"""

import json
import sys
from typing import Any, Dict, List, Optional
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrataSlimsMCPServer:
    """MCP Server for StrataSlims music generation bot."""
    
    def __init__(self):
        self.name = "strataslims"
        self.version = "0.1.0"
        self.description = "StrataSlims MCP server for music generation and Discord bot management"
        
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        logger.info("Initializing StrataSlims MCP server")
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False
                },
                "resources": {
                    "subscribe": False,
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }
    
    async def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools."""
        tools = [
            {
                "name": "generate_music",
                "description": "Generate music using Suno AI API",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Music generation prompt"
                        },
                        "style": {
                            "type": "string",
                            "description": "Music style/genre",
                            "default": "pop"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "check_credits",
                "description": "Check remaining Suno AI credits",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "parse_music_request",
                "description": "Parse and validate music generation request",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Raw text to parse for music parameters"
                        }
                    },
                    "required": ["text"]
                }
            }
        ]
        
        return {"tools": tools}
    
    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution requests."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "generate_music":
                return await self._generate_music(arguments)
            elif tool_name == "check_credits":
                return await self._check_credits(arguments)
            elif tool_name == "parse_music_request":
                return await self._parse_music_request(arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def _generate_music(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate music using Suno AI."""
        try:
            # Import here to avoid circular imports
            from bot.sunoapi import generate_music, wait_for_completion
            
            prompt = arguments.get("prompt", "")
            style = arguments.get("style", "pop")
            
            if not prompt:
                raise ValueError("Prompt is required for music generation")
            
            # Generate music (this is a simplified version)
            result = await generate_music(prompt, style)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Music generation initiated for prompt: '{prompt}' in style: '{style}'\nResult: {result}"
                    }
                ]
            }
        except Exception as e:
            raise Exception(f"Music generation failed: {str(e)}")
    
    async def _check_credits(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check remaining Suno AI credits."""
        try:
            from bot.sunoapi import get_remaining_credits
            
            credits = await get_remaining_credits()
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Remaining Suno AI credits: {credits}"
                    }
                ]
            }
        except Exception as e:
            raise Exception(f"Failed to check credits: {str(e)}")
    
    async def _parse_music_request(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Parse music generation request text."""
        try:
            from bot.musicparser import parse_music_prompt
            
            text = arguments.get("text", "")
            
            if not text:
                raise ValueError("Text is required for parsing")
            
            parsed = parse_music_prompt(text)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Parsed music request: {json.dumps(parsed, indent=2)}"
                    }
                ]
            }
        except Exception as e:
            raise Exception(f"Failed to parse music request: {str(e)}")

async def main():
    """Main MCP server function."""
    server = StrataSlimsMCPServer()
    
    try:
        while True:
            # Read JSON-RPC message from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            try:
                message = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            
            method = message.get("method")
            params = message.get("params", {})
            request_id = message.get("id")
            
            response = None
            
            if method == "initialize":
                result = await server.handle_initialize(params)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            elif method == "tools/list":
                result = await server.handle_tools_list(params)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            elif method == "tools/call":
                result = await server.handle_tools_call(params)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            if response:
                print(json.dumps(response), flush=True)
                
    except KeyboardInterrupt:
        logger.info("MCP server shutting down")
    except Exception as e:
        logger.error(f"MCP server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())