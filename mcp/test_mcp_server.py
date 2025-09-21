#!/usr/bin/env python3
"""
Test script for the MCP Flood Alert Server
This script tests individual MCP tools and the complete workflow.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

from utils.orchestration.check_user_input import classify_location
from utils.orchestration.flood_alert_orchestrator import FloodAlertOrchestrator

async def test_individual_components():
    """Test individual components of the system"""
    print("🧪 Testing Individual Components")
    print("=" * 40)
    
    orchestrator = FloodAlertOrchestrator()
    await orchestrator.initialize()
    
    # Test 1: Flood Analysis
    print("\n1. Testing Flood Analysis...")
    # sample_text = "Heavy rain causing flooding in downtown area. Roads are impassable!"
    sample_text = "Pahang flooding is insane right now! 🌊 Stuck at Kota Bahru, water everywhere. Myvi vs flood = flood wins 😅 Community spirit strong though - everyone helping each other! Stay safe everyone! #PahangFloods #Malaysia #StaySafe"
    flood_analysis = await orchestrator.process_flood_report(sample_text)
    print(f"   Result: {flood_analysis.get('status', 'unknown')}")
    
    # Test 2: Location Classification
    print("\n2. Testing Location Classification...")
    try:
        location_data = classify_location(
            orchestrator.bedrock_handler,
            orchestrator.bedrock_agent_runtime_client,
            "Kuala Lumpur",
            orchestrator.s3_handler
        )
        print(f"   State: {location_data.get('state', 'unknown')}")
        print(f"   District: {location_data.get('district', 'unknown')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Twitter Search
    print("\n3. Testing Twitter Search...")
    try:
        twitter_data = await orchestrator._search_twitter_flood_reports("Kuala Lumpur")
        print(f"   Status: {twitter_data.get('status', 'unknown')}")
        if twitter_data.get('data', {}).get('meta'):
            print(f"   Tweet count: {twitter_data['data']['meta'].get('result_count', 0)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Weather API
    print("\n4. Testing Weather API...")
    try:
        weather_data = await orchestrator._get_weather_forecast("Kuala Lumpur")
        print(f"   Status: {weather_data.get('status', 'unknown')}")
        if weather_data.get('data'):
            print(f"   Weather entries: {len(weather_data['data'])}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Flood Warnings
    print("\n5. Testing Flood Warning API...")
    try:
        flood_warnings = await orchestrator._get_flood_warnings("Kuala Lumpur")
        print(f"   Status: {flood_warnings.get('status', 'unknown')}")
        if flood_warnings.get('data'):
            print(f"   Total warnings: {flood_warnings['data'].get('total_warnings', 0)}")
            print(f"   Location-specific: {flood_warnings['data'].get('location_specific_warnings', 0)}")
    except Exception as e:
        print(f"   Error: {e}")

async def test_complete_workflow():
    """Test the complete workflow with different scenarios"""
    print("\n\n🔄 Testing Complete Workflow")
    print("=" * 40)
    
    orchestrator = FloodAlertOrchestrator()
    
    # Test scenarios
    test_cases = [
        {
            "name": "Valid Flood Report",
            "text": "Pahang flooding is insane right now! 🌊 Stuck at Kota Bahru, water everywhere. Myvi vs flood = flood wins 😅 Community spirit strong though - everyone helping each other! Stay safe everyone! #PahangFloods #Malaysia #StaySafe",
            "expected": "completed"
        },
        {
            "name": "Non-Flood Report",
            "text": "Beautiful sunny day at the beach! Perfect weather for a picnic with family. #SunnyDay #Beach #Family",
            "expected": "rejected"
        },
        {
            "name": "Ambiguous Report",
            "text": "Heavy rain today, hope it doesn't cause problems. Stay dry everyone!",
            "expected": "completed or rejected"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        print(f"   Input: {test_case['text'][:50]}...")
        
        try:
            result = await orchestrator.process_flood_report(test_case['text'])
            status = result.get('status', 'unknown')
            print(f"   Result: {status}")
            
            if status == "completed":
                flood_detection = result.get('flood_detection', {})
                print(f"   Flood detected: {flood_detection.get('is_flood', False)}")
                print(f"   Location: {flood_detection.get('location', 'Unknown')}")
                print(f"   Severity: {flood_detection.get('severity', 'Unknown')}")
                print(f"   Credibility: {result.get('credibility_score', 0):.2f}")
            elif status == "rejected":
                print(f"   Reason: {result.get('reason', 'Unknown')}")
            
        except Exception as e:
            print(f"   Error: {e}")

async def test_mcp_tools():
    """Test MCP tools directly"""
    print("\n\n🔧 Testing MCP Tools")
    print("=" * 40)
    
    # This would test the MCP server tools directly
    # For now, we'll just show what tools are available
    tools = [
        "analyze_flood_post",
        "classify_location", 
        "search_twitter_flood_reports",
        "get_weather_forecast",
        "get_flood_warning",
        "get_alternative_routes",
        "create_flood_report",
        "send_alert_notification"
    ]
    
    print("Available MCP Tools:")
    for i, tool in enumerate(tools, 1):
        print(f"   {i}. {tool}")
    
    print("\nNote: To test MCP tools directly, run the MCP server and use an MCP client.")

async def main():
    """Main test function"""
    print("🚨 MCP Flood Alert System - Test Suite")
    print("=" * 50)
    
    try:
        # await test_individual_components()
        await test_complete_workflow()
        # await test_mcp_tools()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
