import re
from collections import Counter

SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

def split_sentences(text):
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]

def tokenize(text):
    return re.findall(r"\b[a-zA-Z']{2,}\b", text.lower())

def summarise_text(text, n_sentences=5):
    if not text or not text.strip():
        return ''
    sentences = split_sentences(text)
    if len(sentences) <= n_sentences:
        return '\n'.join(sentences)
    words = tokenize(text)
    freq = Counter(words)
    maxf = max(freq.values()) if freq else 1
    for k in freq:
        freq[k] /= maxf
    scores = {}
    for i, sent in enumerate(sentences):
        words = tokenize(sent)
        if not words:
            scores[i] = 0.0; continue
        scores[i] = sum(freq.get(w,0.0) for w in words) / (len(words)**0.5)
    top_idx = sorted(scores, key=lambda i: scores[i], reverse=True)[:n_sentences]
    top_idx_sorted = sorted(top_idx)
    return '\n'.join(sentences[i] for i in top_idx_sorted)
