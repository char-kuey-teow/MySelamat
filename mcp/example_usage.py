#!/usr/bin/env python3
"""
Example Usage of the MCP Flood Alert System
This script demonstrates how to use the system programmatically.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add the current directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

from utils.orchestration_steps.flood_alert_orchestrator import FloodAlertOrchestrator

async def example_basic_flood_detection():
    """Example: Basic flood detection workflow"""
    print("🔍 Example 1: Basic Flood Detection")
    print("-" * 40)
    
    orchestrator = FloodAlertOrchestrator()
    
    # Sample flood report
    text = "Heavy rain causing severe flooding in downtown area. Roads are completely submerged!"
    
    result = await orchestrator.process_flood_report(text)
    
    print(f"Input: {text}")
    print(f"Status: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'completed':
        flood_detection = result.get('flood_detection', {})
        print(f"Flood detected: {flood_detection.get('is_flood', False)}")
        print(f"Location: {flood_detection.get('location', 'Unknown')}")
        print(f"Severity: {flood_detection.get('severity', 'Unknown')}")
        print(f"Credibility: {result.get('credibility_score', 0):.2f}")

async def example_with_image():
    """Example: Flood detection with image"""
    print("\n🖼️ Example 2: Flood Detection with Image")
    print("-" * 40)
    
    orchestrator = FloodAlertOrchestrator()
    
    # Sample flood report with image
    text = "KL flooding is insane right now! Water everywhere at Mid Valley!"
    image_path = "post_img/midvalley.png"
    
    # Check if image exists
    if Path(image_path).exists():
        result = await orchestrator.process_flood_report(
            text, 
            image_files=[image_path],
            save_to_s3=False
        )
        
        print(f"Input: {text}")
        print(f"Image: {image_path}")
        print(f"Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'completed':
            flood_detection = result.get('flood_detection', {})
            print(f"Flood detected: {flood_detection.get('is_flood', False)}")
            print(f"Location: {flood_detection.get('location', 'Unknown')}")
            print(f"Severity: {flood_detection.get('severity', 'Unknown')}")
            print(f"Summary: {flood_detection.get('summary', 'No summary')}")
    else:
        print(f"Image not found: {image_path}")
        print("Skipping image example")

async def example_non_flood_content():
    """Example: Non-flood content (should be rejected)"""
    print("\n🚫 Example 3: Non-Flood Content (Should be Rejected)")
    print("-" * 40)
    
    orchestrator = FloodAlertOrchestrator()
    
    # Sample non-flood content
    text = "Beautiful sunny day at the beach! Perfect weather for a picnic with family. #SunnyDay #Beach"
    
    result = await orchestrator.process_flood_report(text)
    
    print(f"Input: {text}")
    print(f"Status: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'rejected':
        print(f"Reason: {result.get('reason', 'Unknown')}")
        print("✅ Correctly rejected as non-flood content")
    else:
        print("❌ Should have been rejected")

async def example_credibility_scoring():
    """Example: Understanding credibility scoring"""
    print("\n📊 Example 4: Credibility Scoring")
    print("-" * 40)
    
    orchestrator = FloodAlertOrchestrator()
    
    # High credibility example
    text = "URGENT: Severe flooding in Kuala Lumpur! Multiple areas affected. Stay indoors! #KLFloods #Emergency"
    
    result = await orchestrator.process_flood_report(text)
    
    print(f"Input: {text}")
    print(f"Status: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'completed':
        print(f"Credibility Score: {result.get('credibility_score', 0):.2f}")
        print(f"Severity Level: {result.get('severity_level', 'Unknown')}")
        
        # Show breakdown
        flood_detection = result.get('flood_detection', {})
        twitter_data = result.get('twitter_verification', {})
        weather_data = result.get('weather_conditions', {})
        
        print("\nCredibility Breakdown:")
        print(f"- MLLM Analysis: {flood_detection.get('is_flood', False)}")
        print(f"- Twitter Verification: {twitter_data.get('status') == 'success'}")
        print(f"- Weather Confirmation: {weather_data.get('status') == 'success'}")
        print(f"- Location Confidence: {flood_detection.get('location', '') != ''}")

async def example_recommendations():
    """Example: Understanding recommendations"""
    print("\n💡 Example 5: Recommendations")
    print("-" * 40)
    
    orchestrator = FloodAlertOrchestrator()
    
    # Critical flood example
    text = "CRITICAL: Massive flooding in Selangor! Evacuation orders issued! Multiple casualties reported! #Emergency #Flood #Selangor"
    
    result = await orchestrator.process_flood_report(text)
    
    print(f"Input: {text}")
    print(f"Status: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'completed':
        recommendations = result.get('recommendations', [])
        print(f"\nRecommendations ({len(recommendations)}):")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        print(f"\nSeverity Level: {result.get('severity_level', 'Unknown')}")
        print(f"Credibility Score: {result.get('credibility_score', 0):.2f}")

async def example_error_handling():
    """Example: Error handling"""
    print("\n⚠️ Example 6: Error Handling")
    print("-" * 40)
    
    orchestrator = FloodAlertOrchestrator()
    
    # Empty input
    text = ""
    
    try:
        result = await orchestrator.process_flood_report(text)
        print(f"Input: (empty)")
        print(f"Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'rejected':
            print(f"Reason: {result.get('reason', 'Unknown')}")
        
    except Exception as e:
        print(f"Error handled: {e}")

async def main():
    """Run all examples"""
    print("🚨 MCP Flood Alert System - Usage Examples")
    print("=" * 50)
    
    try:
        await example_basic_flood_detection()
        await example_with_image()
        await example_non_flood_content()
        await example_credibility_scoring()
        await example_recommendations()
        await example_error_handling()
        
        print("\n✅ All examples completed successfully!")
        print("\n📚 Next Steps:")
        print("1. Run 'python start_mcp_server.py' to start the MCP server")
        print("2. Run 'python test_mcp_server.py' to run the test suite")
        print("3. Check 'README_MCP.md' for detailed documentation")
        
    except Exception as e:
        print(f"\n❌ Examples failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
