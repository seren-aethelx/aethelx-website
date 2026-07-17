from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os
import re
import hashlib
import datetime
import base64

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.environ.get("HF_API_KEY", "")
HF_TEXT_MODEL_URL = "https://api-inference.huggingface.co/models/Hello-SimpleAI/chatgpt-detector-roberta"
HF_IMAGE_MODEL_URL = "https://api-inference.huggingface.co/models/dima806/deepfake_vs_real_image_detection"


def detect_with_hf(text):
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": text[:512]}
        response = requests.post(HF_TEXT_MODEL_URL, headers=headers, json=payload, timeout=30)
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            scores = result[0]
            fake_score = 0
            real_score = 0
            for item in scores:
                if item['label'].lower() in ['label_0', 'human', 'real']:
                    real_score = item['score']
                elif item['label'].lower() in ['label_1', 'ai', 'chatgpt', 'fake']:
                    fake_score = item['score']
            if fake_score == 0 and real_score == 0:
                for item in scores:
                    if item['score'] > 0.5:
                        if 'human' in item['label'].lower() or item['label'] == 'LABEL_0':
                            real_score = item['score']
                            fake_score = 1 - real_score
                        else:
                            fake_score = item['score']
                            real_score = 1 - fake_score
            return round(real_score * 100), round(fake_score * 100), True
    except Exception as e:
        print(f"HF Text error: {e}")
    return None, None, False


def fallback_analyze(text):
    words = text.split()
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 4]
    transitions = ['furthermore','additionally','moreover','however','consequently','nevertheless','therefore','in conclusion','in summary','it is important','it should be noted','as a result','on the other hand','notably','significantly']
    lc = text.lower()
    trans_score = min(sum(1 for t in transitions if t in lc) * 8, 32)
    avg_len = len(words) / max(len(sentences), 1)
    sent_score = 30 if 14 < avg_len < 28 else 0
    human_punct = len(re.findall(r'[—–…\'\'""\(\)]', text))
    punct_score = 20 if human_punct < 2 else 0
    unique = set(w.lower().strip('.,!?') for w in words)
    rich_score = 10 if len(unique)/max(len(words),1) < 0.55 else 0
    starters = [' '.join(s.split()[:2]).lower() for s in sentences]
    rep_score = 15 if len(set(starters))/max(len(starters),1) < 0.7 else 0
    ai_score = min(trans_score + sent_score + punct_score + rich_score + rep_score, 97)
    return max(100 - ai_score, 3), ai_score


def build_signals(trust_score, ai_probability, used_hf):
    signals = []
    if used_hf:
        if ai_probability > 70:
            signals.append({"type":"positive","icon":"⚡","title":"AI Detected — High Confidence","desc":f"RoBERTa model detected strong AI patterns. AI probability: {ai_probability}%."})
        elif ai_probability > 40:
            signals.append({"type":"positive","icon":"⚡","title":"Mixed Signals Detected","desc":f"Both AI and human patterns found. AI probability: {ai_probability}%."})
        else:
            signals.append({"type":"negative","icon":"✓","title":"Human Writing Detected","desc":f"Strong human writing patterns found. AI probability: {ai_probability}%."})
        signals.append({"type":"negative" if trust_score > 60 else "positive","icon":"🤖","title":"Powered by: chatgpt-detector-roberta","desc":"ML model trained to detect ChatGPT-generated content."})
    else:
        signals.append({"type":"positive" if ai_probability > 50 else "negative","icon":"⚡","title":"Heuristic Analysis","desc":"Pattern-based detection. AI model warming up — try again in 20 seconds."})
    return signals


def detect_image_deepfake(image_data):
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        response = requests.post(HF_IMAGE_MODEL_URL, headers=headers, data=image_data, timeout=60)
        print(f"Image HF Status: {response.status_code}, Response: {response.text[:300]}")
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            scores = result[0] if isinstance(result[0], list) else result
            fake_score = 0
            real_score = 0
            for item in scores:
                label = item.get('label', '').lower()
                score = item.get('score', 0)
                if label in ['fake', 'deepfake', 'label_1', 'artificial']:
                    fake_score = score
                elif label in ['real', 'genuine', 'label_0', 'authentic']:
                    real_score = score
            if fake_score == 0 and real_score == 0 and len(scores) >= 2:
                real_score = scores[0]['score']
                fake_score = scores[1]['score']
            deepfake_prob = round(fake_score * 100)
            real_prob = round(real_score * 100)
            return {"success":True,"deepfake_probability":deepfake_prob,"real_probability":real_prob,"verdict":"DEEPFAKE" if deepfake_prob > 50 else "AUTHENTIC","confidence":max(deepfake_prob, real_prob),"model":"deepfake_vs_real_image_detection"}
    except Exception as e:
        print(f"Image detection error: {e}")
    return {"success":False,"error":"Model loading. Please try again in 30 seconds.","deepfake_probability":0,"real_probability":0,"verdict":"UNKNOWN","confidence":0,"model":"error"}


def generate_cert_id(text, trust_score):
    raw = f"{text[:100]}{trust_score}{datetime.datetime.utcnow().isoformat()}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    return f"AXT-{h[:4]}-{h[4:8]}-{h[8:12]}"


def extract_writing_style(text):
    words = text.split()
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 4]
    unique_words = set(w.lower().strip('.,!?;"\'') for w in words)
    return {
        "vocab_richness": round((len(unique_words)/max(len(words),1))*100),
        "avg_sentence_length": round(len(words)/max(len(sentences),1)),
        "punctuation_variety": len(re.findall(r'[—–…\'\'""\(\)!?;:]', text)),
        "avg_word_length": round(sum(len(w) for w in words)/max(len(words),1), 1),
        "word_count": len(words),
        "sentence_count": len(sentences)
    }


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    text = data['text'].strip()
    if len(text) < 30:
        return jsonify({"error": "Text too short. Minimum 30 characters."}), 400
    trust_score, ai_probability, used_hf = detect_with_hf(text)
    if trust_score is None:
        trust_score, ai_probability = fallback_analyze(text)
        used_hf = False
    return jsonify({"trust":trust_score,"ai_probability":ai_probability,"signals":build_signals(trust_score,ai_probability,used_hf),"model":"chatgpt-detector-roberta" if used_hf else "heuristic-fallback"})


@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    try:
        if 'image' in request.files:
            image_data = request.files['image'].read()
        elif request.is_json:
            data = request.get_json()
            if 'image_base64' not in data:
                return jsonify({"error": "No image provided"}), 400
            b64 = data['image_base64']
            if ',' in b64:
                b64 = b64.split(',')[1]
            image_data = base64.b64decode(b64)
        else:
            return jsonify({"error": "No image provided"}), 400
        if len(image_data) > 5 * 1024 * 1024:
            return jsonify({"error": "Image too large. Maximum 5MB."}), 400
        return jsonify(detect_image_deepfake(image_data))
    except Exception as e:
        print(f"Image route error: {e}")
        return jsonify({"error": "Image processing failed."}), 500


@app.route('/certificate', methods=['POST'])
def generate_certificate():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    text = data.get('text','').strip()
    author_name = data.get('author_name','Anonymous').strip()
    document_title = data.get('document_title','Untitled Document').strip()
    if len(text) < 30:
        return jsonify({"error": "Text too short."}), 400
    trust_score, ai_probability, used_hf = detect_with_hf(text)
    if trust_score is None:
        trust_score, ai_probability = fallback_analyze(text)
        used_hf = False
    if trust_score < 60:
        return jsonify({"error":"Certificate cannot be issued","reason":f"Trust score too low ({trust_score}/100).","trust_score":trust_score,"ai_probability":ai_probability}), 422
    cert_id = generate_cert_id(text, trust_score)
    timestamp = datetime.datetime.utcnow()
    style = extract_writing_style(text)
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:32].upper()
    return jsonify({"certificate_id":cert_id,"status":"VERIFIED","issued_at":timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),"issued_date":timestamp.strftime("%B %d, %Y"),"author_name":author_name,"document_title":document_title,"trust_score":trust_score,"ai_probability":ai_probability,"human_probability":100-ai_probability,"content_hash":content_hash,"word_count":style["word_count"],"writing_style":style,"verdict":"HUMAN AUTHORED","model_used":"chatgpt-detector-roberta" if used_hf else "heuristic-fallback","verify_url":f"https://aethelx.com/verify/{cert_id}","issuer":"AETHELX AI Trust Infrastructure","version":"1.0"})


@app.route('/', methods=['GET'])
def home():
    return send_file('index.html')


@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "AETHELX API running", "version": "0.5"})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=7860)