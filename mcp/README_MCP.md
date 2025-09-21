# AI-Driven Natural Disaster Alert System - MCP Backend

This project implements an AI-driven natural disaster alert system using MCP (Model Context Protocol) for orchestration and MLLM (Multimodal Large Language Model) for intelligent analysis.

## 🏗️ Architecture Overview

The system follows a two-stage approach:

### Stage 1: MLLM as "Gatekeeper"
- **Purpose**: Analyze social media posts (text + images) for flood detection
- **Function**: `analyze_flood_post()` in `check_user_input.py`
- **Output**: Structured data with flood detection, location, severity, and confidence
- **Decision**: If not credible, process stops to avoid wasting API calls

### Stage 2: MCP Orchestration
- **Purpose**: Coordinate multiple data sources and APIs
- **Function**: MCP server with 8 specialized tools
- **Process**: Cross-check with Twitter, Weather API, Official Flood Warnings
- **Output**: Consolidated flood report with credibility scoring

## 🛠️ MCP Tools

The MCP server provides the following tools:

1. **`analyze_flood_post`** - MLLM-based flood detection
2. **`classify_location`** - Malaysian geography classification
3. **`search_twitter_flood_reports`** - Twitter API integration
4. **`get_weather_forecast`** - Weather data from data.gov.my
5. **`get_flood_warning`** - Official flood warnings
6. **`get_alternative_routes`** - Google Maps routing (placeholder)
7. **`create_flood_report`** - Consolidated report generation
8. **`send_alert_notification`** - Email alert system (placeholder)

## 📁 Project Structure

```
mySelamat - Copy/
├── mcp_server.py                 # Main MCP server implementation
├── flood_alert_orchestrator.py  # Complete workflow orchestrator
├── test_mcp_server.py           # Test suite
├── mcp_config.json             # MCP server configuration
├── check_user_input.py         # MLLM analysis functions
├── tweet.py                    # Twitter API integration
├── weather.py                  # Weather API integration
├── config_setting.py           # Configuration management
├── utils/bedrock.py            # AWS Bedrock utilities
└── requirements.txt            # Python dependencies
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file with:

```env
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
WEATHER_LOCATION_KB_ID=your_knowledge_base_id
```

### 3. Run the MCP Server

```bash
python mcp_server.py
```

### 4. Test the System

```bash
python test_mcp_server.py
```

### 5. Run Complete Demo

```bash
python flood_alert_orchestrator.py
```

## 🔄 Workflow Example

```python
# 1. MLLM Analysis (Gatekeeper)
flood_analysis = analyze_flood_post(
    bedrock_handler,
    "KL flooding is insane right now! Water everywhere!",
    image_files=['flood_image.jpg']
)

# If flood detected, continue with MCP orchestration
if flood_analysis['is_flood']:
    # 2. Location Classification
    location_data = classify_location(bedrock_handler, location)
    
    # 3. Twitter Verification
    twitter_data = search_twitter_flood_reports(location)
    
    # 4. Weather Check
    weather_data = get_weather_forecast(location)
    
    # 5. Official Warnings
    flood_warnings = get_flood_warning(location)
    
    # 6. Create Consolidated Report
    report = create_flood_report(
        flood_analysis, location_data, 
        twitter_data, weather_data, flood_warnings
    )
```

## 📊 Credibility Scoring

The system calculates credibility scores based on:

- **MLLM Analysis** (40%): Base confidence from AI analysis
- **Twitter Verification** (25%): Social media confirmation
- **Weather Confirmation** (25%): Meteorological data alignment
- **Location Confidence** (10%): Geographic accuracy

## ⚠️ Severity Levels

- **Minor**: Low impact, localized flooding
- **Moderate**: Significant impact, multiple areas affected
- **Severe**: High impact, widespread flooding
- **Critical**: Extreme impact, life-threatening conditions

## 🔧 Configuration

The system uses `mcp_config.json` for configuration:

- Tool definitions and schemas
- Workflow steps and dependencies
- API endpoints
- Credibility scoring weights
- Severity level descriptions

## 🧪 Testing

Run the test suite to validate all components:

```bash
python test_mcp_server.py
```

The test suite covers:
- Individual component testing
- Complete workflow testing
- Different scenario validation
- Error handling verification

## 📈 Future Enhancements

1. **Google Maps Integration**: Real alternative routing
2. **Database Storage**: Persistent report storage
3. **Email Alerts**: Automated notification system
4. **Real-time Monitoring**: Continuous social media monitoring
5. **Mobile App**: User interface for reporting
6. **Machine Learning**: Improved credibility scoring
