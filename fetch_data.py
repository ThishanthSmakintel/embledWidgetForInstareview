import requests
import json
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

def get_s3_audio_url(voice_filename):
    """Get S3 presigned URL using boto3"""
    S3_BUCKET = os.getenv("S3_BUCKET")
    
    if voice_filename and S3_BUCKET:
        try:
            s3_client = boto3.client('s3')
            s3_key = f"voice/{voice_filename}"
            url = s3_client.generate_presigned_url('get_object', 
                                                 Params={'Bucket': S3_BUCKET, 'Key': s3_key},
                                                 ExpiresIn=3600)
            return url
        except:
            pass
    return 'https://www.soundjay.com/misc/sounds/bell-ringing-05.wav'

def fetch_api_data():
    """Fetch data from AWS API"""
    try:
        url = os.getenv("API_URL")
        response = requests.get(url)
        return response.json() if response.status_code == 200 else []
    except:
        return []

def process_api_data(api_data):
    """Extract metadata and quess columns from API data"""
    processed_reviews = []
    
    for item in api_data:
        if isinstance(item, dict) and item.get('id') in ('1757322288349', '1757322711026'):
            quess_data = item.get('quess', [])
            metadata = item.get('metaData', {})
            transcript = item.get('transcribe', '')
            
            # Parse metadata if it's a string
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            # Get feedback analysis
            feedback_analysis = metadata.get('feedbackAnalysis', {}) if isinstance(metadata, dict) else {}
            
            # Calculate average rating
            avg_rating = round(sum(q.get('answer', 0) for q in quess_data) / len(quess_data)) if quess_data else 3
            
            # Mask email more securely
            email = item.get('userEmail', '')
            if '@' in email:
                domain = email.split('@')[1]
                masked_email = email[0] + '***@***.' + domain.split('.')[-1]
            else:
                masked_email = 'u***@***.com'
            
            text = transcript or 'No transcript available'
            
            # Get audio duration
            audio_duration = metadata.get('audioDurationSec', 0) if isinstance(metadata, dict) else 0
            
            review = {
                'name': masked_email,
                'date': item.get('submittedAt', 'Recent')[:10] if item.get('submittedAt') else 'Recent',
                'rating': avg_rating,
                'text': text,
                'audio': get_s3_audio_url(item.get('voiceFileName', '')),
                'duration': audio_duration,
                'sentiment': feedback_analysis.get('overallSentiment', 'Neutral'),
                'tone': feedback_analysis.get('tonePrimary', 'Neutral'),
                'complaints': feedback_analysis.get('complaintsDetected', False)
            }
            processed_reviews.append(review)
    
    return processed_reviews

def get_processed_reviews():
    """Get processed reviews from API"""
    api_data = fetch_api_data()
    processed_reviews = process_api_data(api_data)
    
    return {
        "company": {"companyName": "API Company", "city": "Unknown", "industry": "Unknown"},
        "reviews": processed_reviews
    }

if __name__ == "__main__":
    data = get_processed_reviews()
    print(f"Found {len(data['reviews'])} reviews")
    for review in data['reviews']:
        print(f"Rating: {review['rating']}, Sentiment: {review['sentiment']}, Text: {review['text']}...")