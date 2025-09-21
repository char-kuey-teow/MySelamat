import json
from config_setting import Config
from sagemaker.predictor import Predictor
from sagemaker.session import Session
import boto3

def forecast_flood(input_data):
    # Create boto3 session with region``
    boto_sess = boto3.Session(
        Config.AWS_ACCESS_KEY, 
        Config.AWS_SECRET_ACCESS_KEY, 
        region_name=Config.BEDROCK_CONFIG["regions"]["N. Virginia"]
    )  

    sm_sess = Session(boto_session=boto_sess)

    predictor = Predictor(endpoint_name=Config.ENDPOINT_NAME, sagemaker_session=sm_sess)
    # Convert input to JSON string
    payload = json.dumps(input_data)

    # Call the endpoint
    response = predictor.predict(payload, initial_args={"ContentType": "application/json"})

    # Parse response
    result = json.loads(response)
    probability = result["prediction"][0][0]

    # Threshold to classify
    if probability > 0.5:
        return {'status': 'success', 'model_prediction': "High Risk of Flood", 'flood_probability': probability} 
    else:
        return {'status': 'success', 'model_prediction': "Low Risk of Flood", 'flood_probability': probability}

# -------------------------------
# Test the function
# -------------------------------
if __name__ == "__main__":
    # -------------------------------
# Dummy input data (12 features: 10 days rainfall + altitude + continent)
# Example values; adjust as needed
# -------------------------------
    dummy_data = {
        "inputs": [12.5, 0.0, 5.0, 8.2, 0.0, 10.1, 3.0, 0.0, 1.2, 6.3, 150.0, 1.0]
    }
    prediction, prob = forecast_flood(dummy_data)
    print(f"Prediction: {prediction}, Probability: {prob}")
