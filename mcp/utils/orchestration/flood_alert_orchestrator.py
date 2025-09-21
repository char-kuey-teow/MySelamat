#!/usr/bin/env python3
"""
Flood Alert Orchestrator
This script demonstrates the complete workflow of the AI-driven natural disaster alert system.
It shows how MLLM acts as the gatekeeper and MCP orchestrates the response.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import sys

from utils.aws_client import SESHandler

# Add the current directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

from utils.orchestration.check_user_input import analyze_flood_post, classify_location, init_bedrock
from utils.orchestration.ml_inference import forecast_flood
from utils.orchestration.tweet import search_tweets
from utils.orchestration.weather import get_weather
from config_setting import Config
from utils.aws_client import S3Handler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FloodAlertOrchestrator:
    """Main orchestrator for the flood alert system"""
    
    def __init__(self):
        self.bedrock_handler = None
        self.bedrock_agent_runtime_client = None
        self.s3_handler = None
        self.initialized = False
        self.ses_client = None
    
    async def initialize(self):
        """Initialize all required services"""
        try:
            logger.info("Initializing services...")
            self.bedrock_handler, self.bedrock_agent_runtime_client = init_bedrock()
            self.s3_handler = S3Handler(
                Config.AWS_ACCESS_KEY, 
                Config.AWS_SECRET_ACCESS_KEY, 
                region_name=Config.BEDROCK_CONFIG["regions"]["N. Virginia"]
            )
            self.ses_client = SESHandler(
                Config.AWS_ACCESS_KEY, 
                Config.AWS_SECRET_ACCESS_KEY, 
                region_name=Config.BEDROCK_CONFIG["regions"]["N. Virginia"]
            )
            self.initialized = True
            logger.info("Services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def process_flood_report(self, 
                                 text_input: str, 
                                 image_files: Optional[list] = None,
                                 image_urls: Optional[list] = None,
                                 save_to_s3: bool = False,
                                 s3_bucket: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete workflow for processing a flood report
        
        Args:
            text_input: Text content from social media post
            image_files: Optional list of image file paths
            save_to_s3: Whether to save images to S3
            s3_bucket: S3 bucket name for image storage
            
        Returns:
            Complete flood report with all data sources
        """
        print('process_flood_report text_input: ', text_input)
        if not self.initialized:
            await self.initialize()
        
        logger.info("Starting flood report processing...")
        
        # Step 1: MLLM as the "gatekeeper" - analyze flood post
        logger.info("Step 1: MLLM analysis (gatekeeper)")
        flood_analysis = analyze_flood_post(
            self.bedrock_handler,
            text_input,
            image_files,
            image_urls,
            self.s3_handler if save_to_s3 else None,
            save_to_s3,
            s3_bucket
        )
        
        logger.info(f"Flood analysis result: {flood_analysis['is_flood']}")
        
        # If MLLM determines it's not a flood, stop processing
        if not flood_analysis['is_flood']:
            logger.info("MLLM determined this is not a flood. Stopping processing.")
            return {
                "status": "rejected",
                "reason": "Not identified as flood by MLLM",
                "flood_analysis": flood_analysis
            }
        
        # Step 2: MCP orchestration - gather additional data
        logger.info("Step 2: MCP orchestration - gathering additional data")
        
        # Extract location from flood analysis
        location = flood_analysis.get('location', '')
        if not location:
            logger.warning("No location found in flood analysis")
            return {
                "status": "incomplete",
                "reason": "No location identified",
                "flood_analysis": flood_analysis
            }
        
        # Classify location
        logger.info(f"Classifying location: {location}")
        location_data = classify_location(
            self.bedrock_handler,
            self.bedrock_agent_runtime_client,
            location,
            self.s3_handler
        )

        # Step 3: Model flood prediction using forecast_flood
        logger.info("Step 3: Model flood prediction using trained classification ML")

        model_input = {
            "inputs": [12.5, 0.0, 5.0, 8.2, 0.0, 10.1, 3.0, 0.0, 1.2, 6.3, 150.0, 1.0]
        }
        try:
            model_pred_result = forecast_flood(model_input)
        except Exception as e:
            logger.error(f"Model prediction failed: {e}")
            model_pred_result = {"status":"failed", "error": str(e)}
        logger.info("Model Prediction Result: ", model_pred_result)

        # Search Twitter for additional reports
        logger.info("Searching Twitter for additional flood reports...")
        twitter_q = [location_data['ordered_locations'][0], 'Malaysia']
        twitter_data = await self._search_twitter_flood_reports(twitter_q)
        
        # Get weather forecast
        logger.info("Getting weather forecast...")
        weather_data = await self._get_weather_forecast(location_data['ordered_locations'])
        
        # Get official flood warnings
        logger.info("Getting official flood warnings...")
        flood_warning_data = await self._get_flood_warnings(location_data['ordered_locations'])
        
        # Create consolidated report
        logger.info("Creating consolidated flood report...")
        consolidated_report = self._create_consolidated_report(
            model_pred_result,
            flood_analysis,
            location_data,
            twitter_data,
            weather_data,
            flood_warning_data,
            model_pred_result
        )

        self._post_report_to_s3(consolidated_report, 'myselamat-user-posts')
        
        logger.info("Flood report processing completed successfully")
        return consolidated_report
    
    async def _search_twitter_flood_reports(self, location) -> Dict[str, Any]:
        """Search Twitter for flood reports in the area"""
        try:
            # Handle both single location string and list of locations
            if isinstance(location, list):
                # Create OR query for multiple locations
                location_query = " OR ".join(location)
                query = f'(banjir OR flood OR 水灾 OR natural disaster) ({location_query}) -is:retweet'
            else:
                # Single location
                query = f'(banjir OR flood OR 水灾 OR natural disaster) {location} -is:retweet'
            tweets = search_tweets(query, max_results=10)
            return {
                "status": "success",
                "data": tweets,
                "query": query
            }
        except Exception as e:
            logger.error(f"Twitter search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "data": {}
            }
    
    async def _get_weather_forecast(self, location: str) -> Dict[str, Any]:
        """Get weather forecast for the location"""
        try:
            weather_data = get_weather(location)
            return {
                "status": "success",
                "data": weather_data
            }
        except Exception as e:
            logger.error(f"Weather API failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "data": []
            }
    
    async def _get_flood_warnings(self, locations: str) -> Dict[str, Any]:
        """Get official flood warnings"""
        try:
            import requests
            url = "https://api.data.gov.my/flood-warning"
            response = requests.get(url)
            response.raise_for_status()
            
            flood_data = response.json()
            
            # Try from most specific (town) to broader (state)
            for location in locations:
                # Filter by station_name, district, or state
                flood_warnings = [
                    station for station in flood_data
                    if location.lower() in station.get("station_name", "").lower()
                    or location.lower() in station.get("station_id", "").lower()
                    or location.lower() in station.get("district", "").lower()
                    or location.lower() in station.get("state", "").lower()
                ]

                if flood_warnings:  # Found match
                    print(f"✅ Found flood warning for '{location}'")
                    return {
                        "status": "success",
                        "data": {
                            "location": location,
                            "matching_stations": flood_warnings,
                            "total_stations": len(flood_data),
                            "matches_found": len(flood_warnings)
                        }
                    }

            print(f"⚠️ None of the locations {locations} were found in API response.")
            return None
            
        except Exception as e:
            logger.error(f"Flood warning API failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "data": {}
            }
    
    def _create_consolidated_report(self, 
                                  model_prediction: Dict,
                                  flood_analysis: Dict,
                                  location_data: Dict,
                                  twitter_data: Dict,
                                  weather_data: Dict,
                                  flood_warning_data: Dict,
                                  model_pred_result: Dict) -> Dict[str, Any]:
        """Create a consolidated flood report"""
        import uuid
        from datetime import datetime
        
        # Calculate credibility score
        credibility_score = self._calculate_credibility_score(
            model_prediction, flood_analysis, twitter_data, weather_data, flood_warning_data
        )
        
        # Determine severity level
        severity_level = self._determine_severity_level(
            model_prediction, flood_analysis, twitter_data, flood_warning_data
        )
        
        # Generate report ID
        report_id = str(uuid.uuid4())
        
        report = {
            "report_id": report_id,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "flood_detection": {
                "is_flood": flood_analysis.get("is_flood", False),
                "location": flood_analysis.get("location", ""),
                "severity": flood_analysis.get("severity", "unknown"),
                "confidence": flood_analysis.get("confidence", 0.0)
            },
            "location_classification": location_data,
            "model_prediction": model_prediction,
            "twitter_verification": twitter_data,
            "weather_conditions": weather_data,
            "official_warnings": flood_warning_data,
            "model_flood_prediction": model_pred_result,
            "credibility_score": credibility_score,
            "severity_level": severity_level,
            "recommendations": self._generate_recommendations(
                model_prediction, flood_analysis, twitter_data, weather_data, flood_warning_data
            )
        }

        results = [report, model_prediction, flood_analysis, location_data, twitter_data, weather_data, flood_warning_data]
        results_text = json.dumps(results, indent=2, ensure_ascii=False)
        system_prompt = (
            "You are a reporting assistant. "
            "Given a list of flood detection results (each with summary, location, and severity), "
            "write a concise, clear paragraph summarizing the overall situation. "
            "The summary should be suitable for a dashboard, "
            "avoiding technical jargon and focusing on clarity and relevance for the public. "
            "Highlight affected locations and severity, and keep the tone informative and neutral."
        )

        user_message = self.bedrock_handler.user_message(
            message=f"Flood detection results:\n{results_text}",
            context=system_prompt
        )

        response =self.bedrock_handler.invoke_model([user_message])

        summary = None
        try:
            contents = response["output"]["message"]["content"]
            summary = " ".join([c["text"] for c in contents if "text" in c]).strip()
        except Exception:
            print("Unable to generate a consolidated report at this time.")
        
        report["summary"] = summary if summary else flood_analysis.get("summary", "")
        return report
    
    def _calculate_credibility_score(self, model_prediction: Dict, flood_data: Dict, twitter_data: Dict, weather_data: Dict, flood_warning_data: Dict) -> float:
        """Calculate credibility score based on multiple data sources"""
        score = 0.0
        
        # Base score from MLLM analysis
        if flood_data.get("is_flood", False):
            score += 0.25

        if flood_warning_data.get("status") == "success" and flood_warning_data.get("data", {}).get("matches_found", 0) > 0:
            score += 0.2

        if model_prediction.get("status") == "success" and model_prediction.get("flood_probability", 0) > 0.5:
            score += 0.1
        
        # Twitter verification bonus
        if twitter_data.get("status") == "success" and twitter_data.get("data", {}).get("meta", {}).get("result_count", 0) > 0:
            score += 0.15
        
        # Weather data confirmation
        if weather_data.get("status") == "success" and weather_data.get("data"):
            score += 0.15
        
        # Location classification confidence
        if flood_data.get("location") and flood_data.get("location") != "unknown":
            score += 0.05
        
        return min(score, 1.0)
    
    def _determine_severity_level(self, model_prediction: Dict, flood_data: Dict, twitter_data: Dict, flood_warning_data: Dict) -> str:
        """Determine overall severity level"""
        severity = flood_data.get("severity", "unknown")
        
        # Upgrade severity based on additional data
        if twitter_data.get("status") == "success":
            tweet_count = twitter_data.get("data", {}).get("meta", {}).get("result_count", 0)
            if tweet_count > 5:
                if severity == "minor":
                    severity = "moderate"
                elif severity == "moderate":
                    severity = "severe"
        
        if flood_warning_data.get("status") == "success":
            warning_count = flood_warning_data.get("data", {}).get("location_specific_warnings", 0)
            if warning_count > 0:
                if severity in ["minor", "moderate"]:
                    severity = "severe"
                elif severity == "severe":
                    severity = "critical"

        if model_prediction.get("status") == "success":
            prediction = model_prediction.get("model_prediction", '')
            if prediction == 'High Risk of Flood':
                if severity in ["minor", "moderate"]:
                    severity = "severe"
                elif severity == "severe":
                    severity = "critical"
        
        return severity
    
    def _generate_recommendations(self, model_prediction: Dict, flood_data: Dict,  
                                twitter_data: Dict, weather_data: Dict, 
                                flood_warning_data: Dict) -> list:
        """Generate recommendations based on the data"""
        recommendations = []
        
        severity = flood_data.get("severity", "unknown")
        credibility_score = self._calculate_credibility_score(model_prediction, flood_data, twitter_data, weather_data, flood_warning_data)

        if model_prediction.get("status") == "success":
            prediction = model_prediction.get("model_prediction", '')
            if prediction == 'High Risk of Flood':
                recommendations.append("High risk of flood predicted")
        
        if credibility_score > 0.7:
            recommendations.append("High credibility - consider immediate alert distribution")
        
        if severity in ["severe", "critical"]:
            recommendations.append("High severity detected - activate emergency protocols")
            recommendations.append("Contact local authorities immediately")
        
        if twitter_data.get("status") == "success" and twitter_data.get("data", {}).get("meta", {}).get("result_count", 0) > 3:
            recommendations.append("Multiple social media reports confirm the incident")
        
        if flood_warning_data.get("status") == "success" and flood_warning_data.get("data", {}).get("location_specific_warnings", 0) > 0:
            recommendations.append("Official flood warnings are active for this area")
        
        if weather_data.get("status") == "success" and weather_data.get("data"):
            recommendations.append("Monitor weather conditions for further developments")
        
        return recommendations
    
    def send_flood_email(self, flood_summary: str):
        """Send flood alert email using AWS SES"""
        from utils.orchestration.send_email import send_flood_email
        try:
            send_flood_email(self.bedrock_handler, self.ses_client, flood_summary)
            logger.info(f"Flood alert email sent.")
        except Exception as e:
            logger.error(f"Failed to send flood alert email: {e}")

    def _post_report_to_s3(self, report: dict, bucket_name: str, s3_key_prefix: str = "flood_reports/") -> str:
        """
        Uploads the consolidated report as a JSON file to the specified S3 bucket.
        Returns the S3 URI of the uploaded file.
        """
        import json
        import uuid
        if not self.s3_handler:
            raise RuntimeError("S3 handler is not initialized. Call initialize() first.")
        # Ensure bucket exists
        if not self.s3_handler.ensure_bucket_exists(bucket_name):
            raise RuntimeError(f"S3 bucket '{bucket_name}' does not exist and could not be created.")
        # Generate unique filename
        report_id = report.get("report_id") or str(uuid.uuid4())
        s3_key = f"{s3_key_prefix}{report_id}.json"
        # Convert report to JSON
        report_json = json.dumps(report, indent=2, ensure_ascii=False)
        # Upload to S3
        self.s3_handler.client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=report_json.encode("utf-8"),
            ContentType="application/json"
        )
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        return s3_uri

async def demo_flood_alert_system():
    """Demonstrate the complete flood alert system"""
    orchestrator = FloodAlertOrchestrator()
    
    # Example flood report
    sample_text = "Pahang flooding is insane right now! 🌊 Stuck at Kota Bahru, water everywhere. Myvi vs flood = flood wins 😅 Community spirit strong though - everyone helping each other! Stay safe everyone! #PahangFloods #Malaysia #StaySafe"
    sample_image = ['post_img/midvalley.png'] if Path('post_img/midvalley.png').exists() else None
    
    print("🚨 AI-Driven Natural Disaster Alert System Demo")
    print("=" * 50)
    print(f"Sample input: {sample_text}")
    print()
    
    try:
        # Process the flood report
        result = await orchestrator.process_flood_report(
            text_input=sample_text,
            image_files=sample_image,
            save_to_s3=True,
            s3_bucket='myselamat-user-posts'
        )
        
        print("📊 PROCESSING RESULT:")
        print("=" * 30)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Display key insights
        if result.get("status") == "completed":
            print("\n🔍 KEY INSIGHTS:")
            print("-" * 20)
            flood_detection = result.get("flood_detection", {})
            print(f"✅ Flood Detected: {flood_detection.get('is_flood', False)}")
            print(f"📍 Location: {flood_detection.get('location', 'Unknown')}")
            print(f"⚠️  Severity: {flood_detection.get('severity', 'Unknown')}")
            print(f"🎯 Credibility Score: {result.get('credibility_score', 0):.2f}")
            print(f"🚨 Overall Severity Level: {result.get('severity_level', 'Unknown')}")
            
            recommendations = result.get("recommendations", [])
            if recommendations:
                print(f"\n💡 RECOMMENDATIONS:")
                print("-" * 20)
                for i, rec in enumerate(recommendations, 1):
                    print(f"{i}. {rec}")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    asyncio.run(demo_flood_alert_system())
