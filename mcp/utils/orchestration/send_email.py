import boto3, json

from config_setting import Config
from check_user_input import init_bedrock
from utils.aws_client import BedrockHandler, SESHandler

def send_flood_email(
        bedrock_handler: BedrockHandler,
        ses_handler: SESHandler,
        flood_summary: str
    ) -> dict:
    """
    Uses Bedrock invoke_model to generate a contextual flood alert email.
    """
    system_prompt = """
    You are a disaster alert assistant.
    Given a JSON flood summary, write a clear and professional email to citizens.
    - Include flood location and severity.
    - Provide a short summary of the situation.
    - Add a polite request to confirm if the flood occurrence is accurate.
    - Email tone should be urgent but reassuring.
    - End with a call-to-action button linking to a confirmation page.
    Respond only in JSON with keys: subject, body_html.
    """

    user_message = bedrock_handler.user_message(
        message=flood_summary,
        context=system_prompt,
    )

    # Call the Nova model
    response = bedrock_handler.invoke_model([user_message])

    model_output = json.loads(response["body"])
    try:
        text_output = model_output["content"][0]["text"]
        email_json = json.loads(text_output)
    except Exception:
        # fallback template if parsing fails
        email_json = {
            "subject": f"Flood Alert: {flood_summary.get('location')}",
            "body_html": f"""
                <h2>🚨 Flood Alert</h2>
                <p>Location: {flood_summary.get('location')}</p>
                <p>Severity: {flood_summary.get('severity')}</p>
                <p>Please confirm if this flood is happening near you.</p>
                <a href="https://example.com/confirm?flood_id={flood_summary.get('id', '123')}"
                   style="display:inline-block;padding:10px 20px;background:#007bff;color:white;
                   text-decoration:none;border-radius:5px;">
                   Confirm Flood Report
                </a>
            """
        }

    ses_handler.send_email(email_json)

# Example usage
if __name__ == "__main__":
    bedrock_handler, bedrock_agent_runtime_client = init_bedrock()
    ses_client = SESHandler(
        Config.AWS_ACCESS_KEY, 
        Config.AWS_SECRET_ACCESS_KEY, 
        region_name=Config.BEDROCK_CONFIG["regions"]["N. Virginia"]
    )
    dummy_summary = "Heavy rains caused severe flooding in Klang town." \
    "location: Klang, Selangor"\
    "severity: severe"
    send_flood_email(dummy_summary)
    print("Flood alert email sent.")
