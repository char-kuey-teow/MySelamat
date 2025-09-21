#!/usr/bin/env python3 
"""
MCP Server for AI-Driven Natural Disaster Alert System
This server provides MCP tools for flood detection, location classification,
and disaster response coordination.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

# Add the current directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Import our existing modules
from utils.orchestration.check_user_input import analyze_flood_post, classify_location, init_bedrock
from utils.orchestration.tweet import search_tweets
from utils.orchestration.weather import get_weather
from config_setting import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("flood-alert-system")

# Global variables for initialized services
bedrock_handler = None
bedrock_agent_runtime_client = None
s3_handler = None

async def initialize_services():
    """Initialize AWS Bedrock and S3 services"""
    global bedrock_handler, bedrock_agent_runtime_client, s3_handler
    
    try:
        bedrock_handler, bedrock_agent_runtime_client = init_bedrock()
        from utils.aws_client import S3Handler
        s3_handler = S3Handler(
            Config.AWS_ACCESS_KEY, 
            Config.AWS_SECRET_ACCESS_KEY, 
            region_name=Config.BEDROCK_CONFIG["regions"]["N. Virginia"]
        )
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    """List all available MCP tools"""
    return ListToolsResult(
        tools=[
            Tool(
                name="analyze_flood_post",
                description="Analyze a social media post (text + images) to detect flood events using MLLM",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text_input": {
                            "type": "string",
                            "description": "Text content from the social media post"
                        },
                        "image_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of image file paths (optional)"
                        },
                        "save_to_s3": {
                            "type": "boolean",
                            "description": "Whether to save images to S3",
                            "default": False
                        },
                        "s3_bucket": {
                            "type": "string",
                            "description": "S3 bucket name for image storage"
                        }
                    },
                    "required": ["text_input"]
                }
            ),
            Tool(
                name="classify_location",
                description="Classify and validate location information for Malaysian geography",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location name to classify"
                        }
                    },
                    "required": ["location"]
                }
            ),
            Tool(
                name="forecast_flood",
                description="Predict flood risk using a trained ML model based on environmental features.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "inputs": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Model input features"
                        }
                    },
                    "required": ["inputs"]
                }
            ),
            Tool(
                name="search_twitter_flood_reports",
                description="Search Twitter for flood-related posts in a specific area",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location to search for flood reports"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of tweets to return",
                            "default": 10
                        }
                    },
                    "required": ["location"]
                }
            ),
            Tool(
                name="get_weather_forecast",
                description="Get weather forecast for a specific location",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location name for weather forecast"
                        }
                    },
                    "required": ["location"]
                }
            ),
            Tool(
                name="get_flood_warning",
                description="Get official flood warning data from data.gov.my API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location to check for flood warnings"
                        }
                    },
                    "required": ["location"]
                }
            ),
            Tool(
                name="get_alternative_routes",
                description="Get alternative routes using Google Maps API when floods block main roads",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "Starting location"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination location"
                        },
                        "avoid_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Areas to avoid due to flooding"
                        }
                    },
                    "required": ["origin", "destination"]
                }
            ),
            Tool(
                name="create_flood_report",
                description="Create a consolidated flood report and store in database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flood_data": {
                            "type": "object",
                            "description": "Flood detection data from analyze_flood_post"
                        },
                        "location_data": {
                            "type": "object",
                            "description": "Location classification data"
                        },
                        "twitter_data": {
                            "type": "object",
                            "description": "Twitter search results"
                        },
                        "weather_data": {
                            "type": "object",
                            "description": "Weather forecast data"
                        },
                        "flood_warning_data": {
                            "type": "object",
                            "description": "Official flood warning data"
                        }
                    },
                    "required": ["flood_data", "location_data"]
                }
            ),
            Tool(
                name="send_alert_notification",
                description="Send email alerts for flood warnings",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "report_id": {
                            "type": "string",
                            "description": "ID of the flood report"
                        },
                        "recipients": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of email addresses to notify"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "Alert priority level"
                        }
                    },
                    "required": ["report_id", "recipients"]
                }
            )
        ]
    )

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        if name == "analyze_flood_post":
            return await handle_analyze_flood_post(arguments)
        elif name == "classify_location":
            return await handle_classify_location(arguments)
        elif name == "search_twitter_flood_reports":
            return await handle_search_twitter(arguments)
        elif name == "get_weather_forecast":
            return await handle_get_weather(arguments)
        elif name == "get_flood_warning":
            return await handle_get_flood_warning(arguments)
        elif name == "get_alternative_routes":
            return await handle_get_alternative_routes(arguments)
        elif name == "create_flood_report":
            return await handle_create_flood_report(arguments)
        elif name == "send_alert_notification":
            return await handle_send_alert_notification(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )

async def handle_analyze_flood_post(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle flood post analysis"""
    text_input = arguments["text_input"]
    image_files = arguments.get("image_files", [])
    save_to_s3 = arguments.get("save_to_s3", False)
    s3_bucket = arguments.get("s3_bucket")
    
    result = analyze_flood_post(
        bedrock_handler,
        text_input,
        image_files,
        s3_handler if save_to_s3 else None,
        save_to_s3,
        s3_bucket
    )
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
    )

async def handle_classify_location(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle location classification"""
    location = arguments["location"]
    
    result = classify_location(
        bedrock_handler,
        bedrock_agent_runtime_client,
        location,
        s3_handler
    )
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
    )

async def handle_search_twitter(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle Twitter search for flood reports"""
    location = arguments["location"]
    max_results = arguments.get("max_results", 10)
    
    # Handle both single location string and list of locations
    if isinstance(location, list):
        # Create OR query for multiple locations
        location_query = " OR ".join(location)
        query = f'(banjir OR flood OR 水灾 OR natural disaster) ({location_query}) -is:retweet'
    else:
        # Single location
        query = f'(banjir OR flood OR 水灾 OR natural disaster) {location} -is:retweet'
    
    try:
        tweets = search_tweets(query, max_results)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(tweets, indent=2))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Twitter search error: {str(e)}")],
            isError=True
        )

async def handle_get_weather(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle weather forecast retrieval"""
    location = arguments["location"]
    
    try:
        weather_data = get_weather(location)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(weather_data, indent=2))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Weather API error: {str(e)}")],
            isError=True
        )

async def handle_get_flood_warning(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle official flood warning retrieval"""
    locations = arguments["location"]
    
    try:
        import requests
        url = "https://api.data.gov.my/flood-warning"
        response = requests.get(url)
        response.raise_for_status()
        
        flood_data = response.json()
        
        result = None
        # Try from most specific (town) to broader (state)
        for location in locations:
            # Filter by station_name, district, or state
            location_warnings = [
                station for station in flood_data
                if location.lower() in station.get("station_name", "").lower()
                or location.lower() in station.get("station_id", "").lower()
                or location.lower() in station.get("district", "").lower()
                or location.lower() in station.get("state", "").lower()
            ]

            if location_warnings:  # Found match
                location_warnings.sort(key=lambda x: x["date"])  # sort by date
                print(f"✅ Found weather for '{location}'")
                result = {
                    "status": "success",
                    "data": {
                        "location": location,
                        "matching_stations": location_warnings,
                        "total_stations": len(flood_data),
                        "matches_found": len(location_warnings)
                    }
                }
                break

        if result is None:
            print(f"⚠️ None of the locations {locations} were found in API response.")
            result = {
                "status": "error",
                "error": "None of the locations were found in API response.",
                "data": {}
            }
    
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Flood warning API error: {str(e)}")],
            isError=True
        )

async def handle_get_alternative_routes(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle Google Maps alternative routing"""
    origin = arguments["origin"]
    destination = arguments["destination"]
    avoid_areas = arguments.get("avoid_areas", [])
    
    # This is a placeholder implementation
    # In a real implementation, you would integrate with Google Maps API
    result = {
        "origin": origin,
        "destination": destination,
        "avoid_areas": avoid_areas,
        "alternative_routes": [
            {
                "route_id": "route_1",
                "summary": "Primary route avoiding flooded areas",
                "duration": "25 minutes",
                "distance": "15.2 km",
                "warnings": ["Avoid Jalan Ampang - reported flooding"]
            },
            {
                "route_id": "route_2", 
                "summary": "Alternative route via highway",
                "duration": "35 minutes",
                "distance": "22.1 km",
                "warnings": ["Longer route but safer"]
            }
        ],
        "status": "success"
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
    )

async def handle_create_flood_report(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle flood report creation and storage"""
    flood_data = arguments["flood_data"]
    location_data = arguments["location_data"]
    twitter_data = arguments.get("twitter_data", {})
    weather_data = arguments.get("weather_data", {})
    flood_warning_data = arguments.get("flood_warning_data", {})
    
    # Generate report ID
    import uuid
    report_id = str(uuid.uuid4())
    
    # Create consolidated report
    report = {
        "report_id": report_id,
        "timestamp": str(asyncio.get_event_loop().time()),
        "flood_detection": flood_data,
        "location_classification": location_data,
        "twitter_verification": twitter_data,
        "weather_conditions": weather_data,
        "official_warnings": flood_warning_data,
        "credibility_score": calculate_credibility_score(flood_data, twitter_data, weather_data),
        "severity_level": determine_severity_level(flood_data, twitter_data, flood_warning_data)
    }
    
    # In a real implementation, you would store this in a database
    # For now, we'll just return the report
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(report, indent=2))]
    )

async def handle_send_alert_notification(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle alert notification sending"""
    report_id = arguments["report_id"]
    recipients = arguments["recipients"]
    priority = arguments.get("priority", "medium")
    
    # This is a placeholder implementation
    # In a real implementation, you would send actual emails
    result = {
        "report_id": report_id,
        "recipients": recipients,
        "priority": priority,
        "status": "sent",
        "message": f"Alert notification sent to {len(recipients)} recipients"
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
    )

def calculate_credibility_score(flood_data: Dict, twitter_data: Dict, weather_data: Dict) -> float:
    """Calculate credibility score based on multiple data sources"""
    score = 0.0
    
    # Base score from MLLM analysis
    if flood_data.get("is_flood", False):
        score += 0.4
    
    # Twitter verification bonus
    if twitter_data.get("data", {}).get("result_count", 0) > 0:
        score += 0.3
    
    # Weather data confirmation
    if weather_data and len(weather_data) > 0:
        score += 0.2
    
    # Location classification confidence
    if flood_data.get("location") and flood_data.get("location") != "unknown":
        score += 0.1
    
    return min(score, 1.0)

def determine_severity_level(flood_data: Dict, twitter_data: Dict, flood_warning_data: Dict) -> str:
    """Determine overall severity level"""
    severity = flood_data.get("severity", "unknown")
    
    # Upgrade severity based on additional data
    if twitter_data.get("data", {}).get("result_count", 0) > 5:
        if severity == "minor":
            severity = "moderate"
        elif severity == "moderate":
            severity = "severe"
    
    if flood_warning_data.get("location_specific_warnings", 0) > 0:
        if severity in ["minor", "moderate"]:
            severity = "severe"
        elif severity == "severe":
            severity = "critical"
    
    return severity

async def main():
    """Main entry point for the MCP server"""
    # Initialize services
    await initialize_services()
    tools_result = await handle_list_tools()
    print("Available MCP Tools:")
    for tool in tools_result.tools:
        print(f"- {tool.name}: {tool.description}")

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="flood-alert-system",
                server_version="1.0.0",
                capabilities={
                    "tools": {},            # enables tools
                    "resources": {},        # enables resources if you want
                    "experimental": {},     # optional experimental features
                },
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
