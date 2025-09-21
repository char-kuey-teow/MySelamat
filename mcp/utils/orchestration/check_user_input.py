import json
import boto3
from pathlib import Path
from typing import Dict, Any, Optional
from utils.aws_client import BedrockHandler, KBHandler, S3Handler
import base64
import time
from config_setting import Config

def init_bedrock():
    bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=Config.BEDROCK_CONFIG["regions"]["N. Virginia"],
            aws_access_key_id=Config.AWS_ACCESS_KEY, 
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
        )
        
    model_id = Config.BEDROCK_CONFIG["multimodal_llms"]["N. Virginia"]["Amazon Nova Lite"]["model"]
                
    model_params = {
        "nova-canvas": Config.BEDROCK_CONFIG["nova_canvas_params"],
        "nova-reel": Config.BEDROCK_CONFIG["nova_reel_params"],
        "nova": Config.BEDROCK_CONFIG["nova_model_params"]
    }

    params = next(
        (params for key, params in model_params.items() if key in model_id),
        Config.BEDROCK_CONFIG["nova_model_params"]
    )

    bedrock_handler = BedrockHandler(bedrock_runtime, model_id, params, Config.AWS_ACCESS_KEY, Config.AWS_SECRET_ACCESS_KEY)

    bedrock_agent_runtime_client = boto3.client(
        "bedrock-agent-runtime",
        region_name=Config.BEDROCK_CONFIG["regions"]["N. Virginia"],
        aws_access_key_id=Config.AWS_ACCESS_KEY, 
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
    )

    return bedrock_handler, bedrock_agent_runtime_client

        
def analyze_flood_post(
    bedrock_handler: BedrockHandler,
    text_input: str,
    image_files: Optional[list[str]] = None,
    image_urls: Optional[list[str]] = None,
    s3_handler: Optional[S3Handler] = None,
    save_to_s3: bool = False,
    s3_bucket: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze a post (text + images) using Nova MLLM via Bedrock
    to determine if it indicates a flood, summarize the content,
    extract location, and severity level.

    Args:
        bedrock_handler (BedrockHandler): Initialized handler for Bedrock model calls
        text_input (str): The text description from user/tweet
        image_files (list[str], optional): List of image file paths (local or uploaded)
        s3_handler (S3Handler, optional): Helper for uploading to S3
        save_to_s3 (bool): If True, upload images to S3 instead of sending base64
        s3_bucket (str, optional): Target S3 bucket if save_to_s3=True

    Returns:
        dict: {
            "is_flood": bool,
            "summary": str,
            "location": str,
            "severity": str,
            "raw_response": dict
        }
    """
    system_prompt = (
        "You are a flood detection assistant. "
        "Given a text description and optional images, determine if it indicates a flood. "
        "If yes, summarize the post, extract the exact location string as it appears in the post, "
        "Classify severity into one of: [minor, moderate, severe, critical]. "
        "Respond in JSON format with keys: is_flood, summary, location, severity."
    )

    if save_to_s3 and image_files:
        image_urls = []
        for img_path in image_files:
            s3_key = f"flood_reports/{Path(img_path).name}"
            s3_handler.client.upload_file(img_path, s3_bucket, s3_key)
            # create presigned URL
            presigned_url = s3_handler.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": s3_bucket, "Key": s3_key},
                ExpiresIn=3600
            )
            image_urls.append(presigned_url)
              
        user_message = bedrock_handler.user_message(
            message=text_input,
            context=system_prompt,
            image_urls=image_urls
        )
    else:
        user_message = bedrock_handler.user_message(
            message=text_input,
            context=system_prompt,
            uploaded_files=image_files,
            image_urls=image_urls        
        )

    # Call the Nova model
    response = bedrock_handler.invoke_model([user_message])

    # Extract structured JSON from model output
    try:
        contents = response["output"]["message"]["content"]
        model_output = " ".join([c["text"] for c in contents if "text" in c])

        # Strip Markdown fences if present
        if model_output.strip().startswith("```"):
            model_output = model_output.strip("`")   # remove backticks
            if model_output.lower().startswith("json"):
                model_output = model_output[4:]  # drop "json" after ```
            model_output = model_output.strip()

        parsed = json.loads(model_output)
    except Exception:
        parsed = {
            "is_flood": False,
            "summary": "Unable to parse model output",
            "location": None,
            "severity": "unknown"
        }

    return {
        "is_flood": parsed.get("is_flood", False),
        "summary": parsed.get("summary", ""),
        "location": parsed.get("location", ""),
        "severity": parsed.get("severity", "unknown"),
        "raw_response": response
    }    

def classify_location(
        bedrock_handler: BedrockHandler,
        bedrock_agent_runtime_client, 
        location: str,
        s3_handler: Optional[S3Handler],
    ):
    base_prompt = f"""
    You are a location classification assistant for Malaysian geography.  
    Given a location name, identify the most accurate category for it.  
    Return the results in strict JSON format with the following keys:  
    
    {{
      "district": "... or None",
      "state": "... or None",
      "division": "... or None",
      "recreation_centre": "... or None",
      "town": "... or None"
    }}

    If a field does not apply, return it as "None".  
    Only return the JSON object, nothing else.  

    Location: {location}
    """
    retriever = KBHandler(
        bedrock_agent_runtime_client,
        Config.BEDROCK_CONFIG["kb_configs"],
        kb_id=Config.WEATHER_LOCATION_KB_ID
    )
   
    docs = retriever.get_relevant_docs(base_prompt)
    kb_context = retriever.parse_kb_output_to_string(docs) if docs else ''
    # --- Step 2: Combine docs + base prompt ---
    final_prompt = base_prompt
    if kb_context:
        final_prompt += f"\n\nRelevant references:\n{kb_context}"
    else:
        obj = s3_handler.client.get_object(
            Bucket="myselamat-us",
            Key="weather_api_locations.md"
        )
        reference_text = obj["Body"].read().decode("utf-8")
        final_prompt += f"\n\nRelevant references:\n{reference_text}"
    
    user_message = bedrock_handler.user_message(
        message=final_prompt,
    )
    # Call the Nova model
    response = bedrock_handler.invoke_model([user_message])
    print('classify_location response: ', response)

    # Extract structured JSON from model output
    try:
        contents = response["output"]["message"]["content"]
        model_output = " ".join([c["text"] for c in contents if "text" in c])

        # Strip Markdown fences if present
        if model_output.strip().startswith("```"):
            model_output = model_output.strip("`")   # remove backticks
            if model_output.lower().startswith("json"):
                model_output = model_output[4:]  # drop "json" after ```
            model_output = model_output.strip()

        parsed = json.loads(model_output)
        # Order results by granularity
        priority_order = ["town", "recreation_centre", "district", "division", "state"]
        ordered_locations = [parsed[key] for key in priority_order if parsed.get(key) and parsed[key] != "None"]
        print('ordered_locations: ', ordered_locations)
    except Exception:
        parsed = {
            "district": None,
            "state": None,
            "division": None,
            "recreation_centre": None,
            "town": None
        }
    
    return {
        "district": parsed.get("district", "unknown"),
        "state": parsed.get("state", "unknown"),
        "division": parsed.get("division", "unknown"),
        "recreation_centre": parsed.get("recreation_centre", "unknown"),
        "town": parsed.get("town", "unknown"),
        "ordered_locations": ordered_locations,
        "raw_response": response
    }   

if __name__ == "__main__":
    bedrock_handler, bedrock_agent_runtime_client = init_bedrock()
    s3_handler = S3Handler(Config.AWS_ACCESS_KEY, Config.AWS_SECRET_ACCESS_KEY, region_name=Config.BEDROCK_CONFIG["regions"]["N. Virginia"])
    # text_input = "KL flooding is insane right now! 🌊 Stuck at Mid Valley, water everywhere. Myvi vs flood = flood wins 😅 Community spirit strong though - everyone helping each other! Stay safe everyone! #KLFloods #Malaysia #StaySafe"
    # image_files = ['post_img\midvalley.png']

    # response = analyze_flood_post(
    #     bedrock_handler,
    #     text_input,
    #     image_files,
    #     s3_handler=s3_handler,
    #     save_to_s3=True,
    #     s3_bucket='myselamat-user-posts'
    # )
    # print(json.dumps(response, indent=2))

    location = classify_location(bedrock_handler, bedrock_agent_runtime_client, "Johor Bahru", s3_handler=s3_handler)
    print(json.dumps(location, indent=2))
