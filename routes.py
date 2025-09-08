import os
import json
import boto3
import requests
from flask import Blueprint, jsonify, render_template

api = Blueprint('api', __name__)
main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/test')
def test_page():
    return render_template('test.html')

@main.route('/restaurant')
def restaurant_page():
    return render_template('restaurant.html')


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
        except Exception as e:
            print(f"Error generating S3 presigned URL: {e}") 
    return 'https://www.soundjay.com/misc/sounds/bell-ringing-05.wav'

def fetch_api_data(business_id):
    """Fetch data from AWS API"""
    try:
        url = "https://mi6hmfm0b5.execute-api.ap-southeast-1.amazonaws.com/prod/company/reviews-no-auth/"
        response = requests.get(url, params={'companyId': business_id})
        return response.json() if response.status_code == 200 else []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching API data: {e}")
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
                except json.JSONDecodeError:
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

@main.route('/widget.js')
def widget_js():
    js_code = """
/*
  NOTE: For production environments, it is highly recommended to serve this JavaScript
  from a static file (.js) rather than embedding it as a multiline string in Python.
  This improves performance, allows for browser caching, and makes development
  (linting, formatting, syntax highlighting) much easier.

  You could use Flask's `send_from_directory` to serve a static JS file.
  Example:
  return send_from_directory('static/js', 'widget.js')
*/
(function() {
  'use strict';
  
  const script = document.currentScript;
  const businessId = script.getAttribute('data-business-id');
  const sanitizedId = businessId.replace(/[^a-zA-Z0-9]/g, '');
  const apiUrl = script.getAttribute('data-api-url') || window.WIDGET_CONFIG?.apiUrl || 'http://localhost:5000';
  const floating = script.getAttribute('data-floating') === 'true';
  const theme = script.getAttribute('data-theme') || 'light';
  
  if (!businessId) {
    console.error('Widget: data-business-id is required');
    return;
  }
  
  const widgetId = 'review-widget-' + businessId;
  const container = document.createElement('div');
  container.id = widgetId;
  
  if (floating) {
    container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;';
    document.body.appendChild(container);
  } else {
    script.parentNode.insertBefore(container, script.nextSibling);
  }
  
  const fontAwesome = document.createElement('link');
  fontAwesome.rel = 'stylesheet';
  fontAwesome.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css';
  document.head.appendChild(fontAwesome);
  
  const style = document.createElement('style');
  style.textContent = `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    #${widgetId} { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    #${widgetId} * { box-sizing: border-box; }
    .widget-card { 
      background: ${theme === 'dark' ? 'linear-gradient(135deg, rgba(17,24,39,0.95) 0%, rgba(31,41,55,0.95) 100%)' : 'linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.95) 100%)'};
      color: ${theme === 'dark' ? '#f9fafb' : '#111827'};
      border-radius: 16px; padding: 16px; width: 280px; min-height: 360px;
      box-shadow: ${theme === 'dark' ? '0 8px 25px rgba(0,0,0,0.4)' : '0 8px 25px rgba(0,0,0,0.15)'};
      backdrop-filter: blur(12px); border: 1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'};
      transition: all 0.3s ease; display: flex; flex-direction: column;
    }
    .widget-card:hover { transform: translateY(-8px) scale(1.02); box-shadow: 0 32px 64px -12px rgba(0,0,0,0.35); }
    .widget-btn { 
      background: #6366f1; color: white; border: none;
      border-radius: 16px; width: 56px; height: 56px; cursor: pointer; font-size: 18px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 8px 25px rgba(99,102,241,0.3);
      display: flex; align-items: center; justify-content: center;
    }
    .widget-btn:hover { transform: scale(1.1) rotate(5deg); box-shadow: 0 12px 35px rgba(99,102,241,0.4); }
    .nav-btn {
      background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
      border-radius: 12px; padding: 10px 16px; cursor: pointer; color: inherit;
      transition: all 0.3s ease; font-weight: 500; backdrop-filter: blur(8px);
    }
    .nav-btn:hover { background: rgba(255,255,255,0.2); transform: translateY(-2px); }
    .avatar { 
      background: #6366f1; 
      box-shadow: 0 8px 25px rgba(99,102,241,0.3);
    }
    .rating-stars { background: linear-gradient(45deg, #fbbf24, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .widget-card { animation: fadeIn 0.6s ease-out; }
  `;
  document.head.appendChild(style);
  
  fetch(`${apiUrl}/api/reviews/${businessId}`)
    .then(res => {
      if (!res.ok) {
        // If response is not 2xx, throw an error to be caught by .catch()
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      return res.json();
    })
    .then(data => renderWidget(data.reviews || []))
    .catch(() => renderErrorWidget());
  
  let currentIndex = 0;
  let widgetReviews = [];
  let currentAudio = null;
  
  function renderWidget(reviews) {
    if (reviews.length === 0) {
      // If there are no reviews, but the company was found, show a message.
      container.innerHTML = `
        <div class="widget-card">
          <div style="text-align:center;margin:auto;padding:20px;">
            <div style="font-size:48px;margin-bottom:16px;">👍</div>
            <div style="font-weight:600;font-size:16px;margin-bottom:8px;">No Reviews Yet</div>
            <div style="font-size:12px;opacity:0.7;">Be the first to leave a review!</div>
          </div>
        </div>
      `;
      return;
    }
    widgetReviews = reviews;
    updateReview();
  }

  function renderErrorWidget() {
    container.innerHTML = `
      <div class="widget-card" style="justify-content:center;align-items:center;text-align:center;">
        <div style="font-size:48px;margin-bottom:16px;">🤔</div>
        <div style="font-weight:600;font-size:16px;margin-bottom:8px;">Company Not Found</div>
        <div style="font-size:12px;opacity:0.7;">Please check the business ID.</div>
      </div>
    `;
  }
  
  function updateReview() {
    const review = widgetReviews[currentIndex];
    const stars = '★'.repeat(review.rating) + '☆'.repeat(5 - review.rating);
    const avgRating = (widgetReviews.reduce((sum, r) => sum + r.rating, 0) / widgetReviews.length).toFixed(1);
    
    container.innerHTML = `
      <div class="widget-card">
        ${floating ? `<button onclick="document.getElementById('${widgetId}').remove()" style="position:absolute;top:16px;right:16px;background:rgba(255,255,255,0.15);border:none;border-radius:12px;width:36px;height:36px;cursor:pointer;font-size:18px;transition:all 0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.25)'" onmouseout="this.style.background='rgba(255,255,255,0.15)'">×</button>` : ''}
        
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
          <div class="rating-stars" style="font-size:16px;font-weight:600;">★★★★★</div>
          <span style="font-weight:600;font-size:14px;">${avgRating}</span>
          <span style="font-size:10px;opacity:0.7;">Rating</span>
          <div style="background:rgba(99,102,241,0.1);color:#6366f1;font-size:10px;font-weight:500;padding:4px 8px;border-radius:12px;">${widgetReviews.length} reviews</div>
        </div>
        
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
          <div class="avatar" style="width:36px;height:36px;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-weight:600;font-size:14px;">${review.name.charAt(0)}</div>
          <div style="flex:1;">
            <div style="font-weight:600;font-size:14px;margin-bottom:2px;">${review.name}</div>
            <div style="color:#fbbf24;font-size:12px;">${stars}</div>
          </div>
        </div>
        
        <div style="background:rgba(99,102,241,0.1);padding:12px;border-radius:12px;margin:12px 0;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
            <button class="widget-btn" onclick="playAudio${sanitizedId}()" style="width:40px;height:40px;font-size:14px;"><i class="fas fa-play"></i></button>
            <div style="flex:1;">
              <div style="font-weight:600;font-size:13px;"><i class="fas fa-headphones"></i> Listen Full Review </div>
              <div style="font-size:10px;opacity:0.7;">Duration: ${Math.floor(review.duration/60)}:${String(review.duration%60).padStart(2,'0')}</div>
            </div>
          </div>
        </div>
        
        <div style="flex:1;min-height:0;">
          <div style="font-size:10px;opacity:0.7;margin-bottom:4px;"><i class="fas fa-comment"></i> Customer Review</div>
          <div style="background:rgba(0,0,0,0.05);padding:8px 12px;border-radius:8px;font-style:italic;border-left:3px solid #6366f1;line-height:1.5;font-size:12px;max-height:100px;overflow-y:hidden;">"${review.text}"</div>
        </div>
        
        ${widgetReviews.length > 1 ? `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;gap:8px;">
          <button class="nav-btn" onclick="prevReview${sanitizedId}()" style="padding:6px 10px;font-size:11px;">←</button>
          <div style="display:flex;gap:4px;">
            ${widgetReviews.map((_, i) => `<div style="width:6px;height:6px;border-radius:50%;background:${i === currentIndex ? '#6366f1' : 'rgba(0,0,0,0.5)'};border:1px solid rgba(255,255,255,0.2);transition:all 0.3s;"></div>`).join('')}
          </div>
          <button class="nav-btn" onclick="nextReview${sanitizedId}()" style="padding:6px 10px;font-size:11px;">→</button>
        </div>` : ''}
        
        <div style="text-align:center;margin-top:auto;padding-top:8px;border-top:1px solid rgba(255,255,255,0.1);">
          <span style="font-size:9px;opacity:0.6;">Powered by </span>
          <a href="https://instareview.ai" target="_blank" style="font-size:9px;font-weight:600;color:#6366f1;text-decoration:none;">InstaReview</a>
        </div>
      </div>
    `;
  }
  
  window['playAudio' + sanitizedId] = function() {
    const btn = container.querySelector('.widget-btn');
    const currentReview = widgetReviews[currentIndex];
    
    if (btn.innerHTML.includes('fa-play')) {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
      }
      
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      
      if (currentReview.audio) {
        currentAudio = new Audio(currentReview.audio);
        currentAudio.play().then(() => {
          btn.innerHTML = '<i class="fas fa-pause"></i>';
        }).catch(() => {
          btn.innerHTML = '<i class="fas fa-play"></i>';
          currentAudio = null;
        });
        
        currentAudio.onended = () => {
          btn.innerHTML = '<i class="fas fa-play"></i>';
          document.getElementById('progress-' + sanitizedId).style.width = '0%';
          currentAudio = null;
        };
        
        currentAudio.ontimeupdate = () => {
          const progress = (currentAudio.currentTime / currentAudio.duration) * 100;
          document.getElementById('progress-' + sanitizedId).style.width = progress + '%';
          document.getElementById('handle-' + sanitizedId).style.left = progress + '%';
        };
      } else {
        setTimeout(() => {
          btn.innerHTML = '<i class="fas fa-pause"></i>';
          setTimeout(() => {
            btn.innerHTML = '<i class="fas fa-play"></i>';
            currentAudio = null;
          }, 3000);
        }, 500);
      }
    } else {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
      }
      btn.innerHTML = '<i class="fas fa-play"></i>';
    }
  };
  
  window['nextReview' + sanitizedId] = function() {
    currentIndex = (currentIndex + 1) % widgetReviews.length;
    updateReview();
  };
  
  window['prevReview' + sanitizedId] = function() {
    currentIndex = (currentIndex - 1 + widgetReviews.length) % widgetReviews.length;
    updateReview();
  };
  
  window['seekAudio' + sanitizedId] = function(event) {
    if (currentAudio) {
      const rect = event.target.getBoundingClientRect();
      const percent = (event.clientX - rect.left) / rect.width;
      currentAudio.currentTime = percent * currentAudio.duration;
    }
  };
  
  let isDragging = false;
  window['startDrag' + sanitizedId] = function(event) {
    isDragging = true;
    event.preventDefault();
    
    const onMouseMove = (e) => {
      if (isDragging && currentAudio) {
        const rect = document.getElementById('progressBar-' + sanitizedId).getBoundingClientRect();
        const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        currentAudio.currentTime = percent * currentAudio.duration;
      }
    };
    
    const onMouseUp = () => {
      isDragging = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
    
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };
})();
    """
    return js_code, 200, {'Content-Type': 'application/javascript'}

@api.route('/reviews/<business_id>')
def get_reviews(business_id):
    api_data = fetch_api_data(business_id)

    # If no data is returned from the API, assume the company is not found.
    if not api_data:
        return jsonify({"error": f"Company with ID '{business_id}' not available or found."}), 404

    processed_reviews = process_api_data(api_data)
    
    response_data = {
        "company": {"companyName": f"Company {business_id}", "city": "Unknown", "industry": "Unknown"},
        "reviews": processed_reviews
    }
    return jsonify(response_data)