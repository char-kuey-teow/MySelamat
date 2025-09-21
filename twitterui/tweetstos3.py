from flask import Flask, request, jsonify
import boto3, json
from datetime import datetime

app = Flask(__name__)

# Your S3 bucket details
S3_BUCKET = "tweets-report-data"
S3_REGION = "ap-southeast-5"  # ✅ only region code

# Initialize S3 client with credentials
s3_client = boto3.client(
    "s3",
    aws_access_key_id="AKIAZYMGMX7BWC42FW2S",
    aws_secret_access_key="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",
    region_name=S3_REGION,
)

@app.route("/post_tweet", methods=["POST"])
def post_tweet():
    try:
        tweet = request.get_json()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_name = f"tweet_{timestamp}.json"

        # Upload tweet JSON to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=file_name,
            Body=json.dumps(tweet, indent=2),
            ContentType="application/json"
        )

        return jsonify({"message": "Tweet saved to S3", "s3_key": file_name}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
