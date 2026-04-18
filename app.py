from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
import hashlib
import datetime

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.environ.get("HF_API_KEY", "")
HF_MODEL_URL = "https://api-inference.huggingface.co/models/Hello-SimpleAI/chatgpt-detector-roberta"

def detect_with_hf(text):
    try:
        print(f"HF_API_KEY set: {bool(HF_API_KEY)}")
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": text[:512]}
        response = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=30)
        print(f"HF Status: {response.status_code}")
        print(f"HF Response: {response.text[:300]}")

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

            ai_probability = round(fake_score * 100)
            trust_score = round(real_score * 100)
            return trust_score, ai_probability, True

    except Exception as e:
        print(f"HF API error: {e}")

    return None, None, False


def fallback_analyze(text):
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 4]

    transitions = [
        'furthermore', 'additionally', 'moreover', 'however',
        'consequently', 'nevertheless', 'therefore', 'in conclusion',
        'in summary', 'it is important', 'it should be noted',
        'as a result', 'on the other hand', 'notably', 'significantly'
    ]
    lc = text.lower()
    trans_count = sum(1 for t in transitions if t in lc)
    trans_score = min(trans_count * 8, 32)

    avg_len = len(words) / max(len(sentences), 1)
    sent_score = 30 if 14 < avg_len < 28 else 0

    human_punct = len(re.findall(r'[—–…\'\'""\(\)]', text))
    punct_score = 20 if human_punct < 2 else 0

    unique = set(w.lower().strip('.,!?') for w in words)
    richness = len(unique) / max(len(words), 1)
    rich_score = 10 if richness < 0.55 else 0

    starters = [' '.join(s.split()[:2]).lower() for s in sentences]
    unique_starters = len(set(starters)) / max(len(starters), 1)
    rep_score = 15 if unique_starters < 0.7 else 0

    ai_score = min(trans_score + sent_score + punct_score + rich_score + rep_score, 97)
    trust_score = max(100 - ai_score, 3)
    return trust_score, ai_score


def build_signals(trust_score, ai_probability, used_hf):
    signals = []
    if used_hf:
        if ai_probability > 70:
            signals.append({"type": "positive", "icon": "⚡", "title": "AI Detected — High Confidence", "desc": f"RoBERTa model detected strong AI patterns. AI probability: {ai_probability}%."})
        elif ai_probability > 40:
            signals.append({"type": "positive", "icon": "⚡", "title": "Mixed Signals Detected", "desc": f"RoBERTa model found both AI and human patterns. AI probability: {ai_probability}%."})
        else:
            signals.append({"type": "negative", "icon": "✓", "title": "Human Writing Detected", "desc": f"RoBERTa model found strong human writing patterns. AI probability: {ai_probability}%."})
        signals.append({"type": "negative" if trust_score > 60 else "positive", "icon": "🤖", "title": "Powered by: chatgpt-detector-roberta", "desc": "ML model trained specifically to detect ChatGPT-generated content."})
    else:
        signals.append({"type": "positive" if ai_probability > 50 else "negative", "icon": "⚡", "title": "Heuristic Analysis", "desc": "Pattern-based detection. AI model warming up — try again in 20 seconds."})
    return signals


def generate_cert_id(text, trust_score):
    """Generate a unique certificate ID based on content hash + timestamp"""
    timestamp = datetime.datetime.utcnow().isoformat()
    raw = f"{text[:100]}{trust_score}{timestamp}"
    hash_val = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    # Format: LMR-XXXX-XXXX-XXXX
    return f"LMR-{hash_val[:4]}-{hash_val[4:8]}-{hash_val[8:12]}"


def extract_writing_style(text):
    """Extract writing style fingerprint signals"""
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 4]

    # Vocabulary richness
    unique_words = set(w.lower().strip('.,!?;"\'') for w in words)
    vocab_richness = round((len(unique_words) / max(len(words), 1)) * 100)

    # Avg sentence length
    avg_sent_len = round(len(words) / max(len(sentences), 1))

    # Punctuation style
    punct_marks = len(re.findall(r'[—–…\'\'""\(\)!?;:]', text))

    # Word length average
    avg_word_len = round(sum(len(w) for w in words) / max(len(words), 1), 1)

    return {
        "vocab_richness": vocab_richness,
        "avg_sentence_length": avg_sent_len,
        "punctuation_variety": punct_marks,
        "avg_word_length": avg_word_len,
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

    signals = build_signals(trust_score, ai_probability, used_hf)
    return jsonify({
        "trust": trust_score,
        "ai_probability": ai_probability,
        "signals": signals,
        "model": "chatgpt-detector-roberta" if used_hf else "heuristic-fallback"
    })


@app.route('/certificate', methods=['POST'])
def generate_certificate():
    """Generate a LUMORA Authorship Certificate"""
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400

    text = data.get('text', '').strip()
    author_name = data.get('author_name', 'Anonymous').strip()
    document_title = data.get('document_title', 'Untitled Document').strip()

    if len(text) < 30:
        return jsonify({"error": "Text too short. Minimum 30 characters."}), 400

    # Run analysis
    trust_score, ai_probability, used_hf = detect_with_hf(text)
    if trust_score is None:
        trust_score, ai_probability = fallback_analyze(text)
        used_hf = False

    # Only issue certificate if trust score is high enough
    if trust_score < 60:
        return jsonify({
            "error": "Certificate cannot be issued",
            "reason": f"Trust score too low ({trust_score}/100). Content shows significant AI patterns.",
            "trust_score": trust_score,
            "ai_probability": ai_probability
        }), 422

    # Generate certificate
    cert_id = generate_cert_id(text, trust_score)
    timestamp = datetime.datetime.utcnow()
    style = extract_writing_style(text)

    # Content hash (for verification)
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:32].upper()

    certificate = {
        "certificate_id": cert_id,
        "status": "VERIFIED",
        "issued_at": timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "issued_date": timestamp.strftime("%B %d, %Y"),
        "author_name": author_name,
        "document_title": document_title,
        "trust_score": trust_score,
        "ai_probability": ai_probability,
        "human_probability": 100 - ai_probability,
        "content_hash": content_hash,
        "word_count": style["word_count"],
        "writing_style": style,
        "verdict": "HUMAN AUTHORED",
        "model_used": "chatgpt-detector-roberta" if used_hf else "heuristic-fallback",
        "verify_url": f"https://lumora.vercel.app/verify/{cert_id}",
        "issuer": "LUMORA AI Trust Infrastructure",
        "version": "1.0"
    }

    return jsonify(certificate)


@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "LUMORA API running", "version": "0.4"})


if __name__ == '__main__':
   app.run(host="0.0.0.0", port=7860)