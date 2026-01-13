from flask import Blueprint, request, jsonify, session, current_app
from app.utils import login_required
from groq import Groq
import os

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return Groq(api_key=api_key)


def generate_ai_reply(message: str) -> str:
    """Real AI using LLaMA‑3‑70B via Groq."""
    client = get_groq_client()
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
