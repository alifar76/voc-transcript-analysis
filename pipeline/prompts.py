"""
Prompt and structured-output schema for the Vertex AI (Gemini) Voice-of-
Customer extraction step. One call transcript in -> one structured JSON
record out.
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "cleaned_transcript": {
            "type": "STRING",
            "description": "The transcript rewritten in clean, readable English, correcting obvious ASR errors while preserving meaning and speaker turns.",
        },
        "summary": {
            "type": "STRING",
            "description": "A one-sentence (<=30 words) summary of what happened on the call.",
        },
        "sentiment": {"type": "STRING", "enum": ["negative", "neutral", "positive"]},
        "sentiment_score": {
            "type": "NUMBER",
            "description": "Sentiment as a continuous score from -1.0 (very negative) to 1.0 (very positive).",
        },
        "is_complaint": {"type": "BOOLEAN"},
        "complaint_category": {
            "type": "STRING",
            "description": "Short category label for the complaint (e.g. 'Overdraft fees'), or 'none' if is_complaint is false.",
        },
        "is_business_opportunity": {
            "type": "BOOLEAN",
            "description": "True if the customer expressed interest in a new or additional product/service (cross-sell or upsell signal).",
        },
        "opportunity_type": {
            "type": "STRING",
            "description": "Short label for the opportunity (e.g. 'High-yield savings interest'), or 'none' if is_business_opportunity is false.",
        },
        "urgency_level": {
            "type": "STRING",
            "enum": ["low", "medium", "high", "critical"],
            "description": "How urgently this call should be followed up on (e.g. fraud or account-takeover signals are critical).",
        },
        "key_topics": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Up to 5 short keyword/topic tags for the call.",
        },
    },
    "required": [
        "cleaned_transcript",
        "summary",
        "sentiment",
        "sentiment_score",
        "is_complaint",
        "complaint_category",
        "is_business_opportunity",
        "opportunity_type",
        "urgency_level",
        "key_topics",
    ],
}

SYSTEM_INSTRUCTION = """You are a Voice-of-Customer (VOC) analytics engine for a retail bank's \
contact center. You are given the raw output of an automatic speech recognition \
(ASR) system that transcribed a real-time phone call between a bank agent \
(labeled AGENT) and a customer (labeled CUST). These raw transcripts are low \
quality: missing punctuation, dropped or misheard words, filler words, \
stutters, and bracketed artifacts like [inaudible] or [crosstalk].

Your job is to read past the noise, reconstruct what was actually said, and \
extract a structured, analyst-ready record from it. Always respond with a \
single JSON object matching the provided schema exactly -- no markdown code \
fences, no commentary outside the JSON."""


def build_user_prompt(lob, raw_transcript):
    return (
        f"Line of business: {lob}\n\n"
        f"Raw ASR call transcript:\n{raw_transcript}\n\n"
        "Extract the structured VOC record for this call now."
    )
