from flask import Blueprint, request, jsonify, session
from app.utils import login_required
from groq import Groq

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")

# IMPORTANT: Insert your Groq API key here
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)


def generate_ai_reply(message: str) -> str:
    """Real AI using LLaMA‑3‑70B via Groq."""
    system_prompt = (
        "You are StudyBuddy AI, a friendly assistant that helps students with learning, "
        "explaining topics, exam preparation, motivation, time management, and university tasks. "
        "Keep answers clear, short and practical."
    )

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        max_tokens=500,
        temperature=0.7
    )

    return completion.choices[0].message.content


@ai_bp.route("/chat", methods=["POST"])
@login_required
def ai_chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"reply": "Please type a question about your studies."})

    reply = generate_ai_reply(message)
    return jsonify({"reply": reply})
