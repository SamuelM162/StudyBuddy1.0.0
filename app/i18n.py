from urllib.parse import urlparse

from flask import current_app, request, session, url_for


DEFAULT_LANGUAGE = "en"


def get_language():
    languages = current_app.config.get("LANGUAGES", [DEFAULT_LANGUAGE])
    selected = session.get("language")
    if selected in languages:
        return selected

    best_match = request.accept_languages.best_match(languages)
    return best_match or current_app.config.get("DEFAULT_LANGUAGE", DEFAULT_LANGUAGE)


def set_language(language):
    languages = current_app.config.get("LANGUAGES", [DEFAULT_LANGUAGE])
    if language in languages:
        session["language"] = language


def tr(en_text, sk_text):
    return en_text if get_language() == "en" else sk_text


def get_return_path():
    candidate = request.form.get("next") or request.args.get("next") or request.referrer
    if not candidate:
        return url_for("main.index")

    parsed = urlparse(candidate)
    if parsed.netloc and parsed.netloc != request.host:
        return url_for("main.index")

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return path
