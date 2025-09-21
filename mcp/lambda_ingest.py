# lambda_ingest.py
import json, uuid, time

from utils.orchestration.flood_alert_orchestrator import FloodAlertOrchestrator
from utils.orchestration.send_email import send_flood_email

async def lambda_handler(event, context):
    # event.body from API Gateway
    body = json.loads(event.get('body') or '{}')
    text = body.get('text_input', '')
    image_files = body.get('image_files')  # base64-encoded strings
    image_urls = body.get('image_urls')  # simple for demo; use presigned upload in prod
    user_id = body.get('user_id', 'anon')
    s3_bucket = body.get('s3_bucket', 'myselamat-user-posts')
    report_id = str(uuid.uuid4())
    start_timestamp = int(time.time())

    orchestrator = FloodAlertOrchestrator()
    await orchestrator.initialize()
    
    sample_text = "Pahang flooding is insane right now! 🌊 Stuck at Kota Bahru, water everywhere. Myvi vs flood = flood wins 😅 Community spirit strong though - everyone helping each other! Stay safe everyone! #PahangFloods #Malaysia #StaySafe"
    flood_analysis = await orchestrator.process_flood_report(sample_text, image_files, image_urls, False, s3_bucket)
    print(f"   Result: {flood_analysis.get('status', 'unknown')}")

    end_timestamp = int(time.time())
    time_taken= end_timestamp - start_timestamp

    orchestrator.send_flood_email(flood_summary=flood_analysis.get('summary', 'No summary available'))
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"report_id": report_id, "status": "completed", "flood_analysis": flood_analysis, "time_taken": time_taken})
    }
