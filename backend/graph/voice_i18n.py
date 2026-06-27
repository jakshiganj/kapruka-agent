"""Localized voice_prompt strings for graph nodes (English, Sinhala, Tamil)."""

from __future__ import annotations

from typing import Any

_MESSAGES: dict[str, dict[str, str]] = {
    "cart_empty": {
        "en": "Your cart is empty. What would you like to order?",
        "si": "ඔබේ කරත්තය හිස්. ඔබට ඇණවුම් කිරීමට අවශ්‍ය දේ කුමක්ද?",
        "ta": "உங்கள் கூடை காலியாக உள்ளது. நீங்கள் என்ன ஆர்டர் செய்ய விரும்புகிறீர்கள்?",
    },
    "need_delivery": {
        "en": "Please tell me the delivery city and date.",
        "si": "කරුණාකර බෙදාහැරීමේ නගරය සහ දිනය කියන්න.",
        "ta": "டெலிவரி நகரம் மற்றும் தேதியைச் சொல்லுங்கள்.",
    },
    "pick_product": {
        "en": (
            "Which gift would you like? Tap one on screen or tell me the name — "
            "for example, the Lavender Love cake."
        ),
        "si": (
            "ඔබට අවශ්‍ය තෑග්ග කුමක්ද? තිරයේ එකක් තෝරන්න හෝ නම කියන්න — "
            "උදාහරණයක් ලෙස Lavender Love cake."
        ),
        "ta": (
            "எந்த பரிசு வேண்டும்? திரையில் ஒன்றைத் தட்டுங்கள் அல்லது பெயரைச் சொல்லுங்கள் — "
            "எ.கா. Lavender Love cake."
        ),
    },
    "added_simple": {
        "en": (
            "Added {name} to your cart — tap the cart icon to review. "
            "Would you like to browse more gifts, or shall we proceed to checkout?"
        ),
        "si": (
            "{name} කරත්තයට එකතු කළා — සමාලෝචනයට cart අයිකනය තෝරන්න. "
            "තව තෑගි බලන්නද, checkout වෙත යන්නද?"
        ),
        "ta": (
            "{name} கூடையில் சேர்க்கப்பட்டது — cart ஐகானைத் தட்டி பாருங்கள். "
            "வேறு பரிசுகள் பார்க்கலாமா, checkout செய்யலாமா?"
        ),
    },
    "added_revalidate": {
        "en": "Added {name} to your cart. I'll check delivery to {city} next.",
        "si": "{name} කරත්තයට එකතු කළා. {city} වෙත බෙදාහැරීම ඊළඟට පරීක්ෂා කරමි.",
        "ta": "{name} கூடையில் சேர்க்கப்பட்டது. {city} டெலிவரியை அடுத்து சரிபார்க்கிறேன்.",
    },
    "checkout_form_empty": {
        "en": (
            "I've opened the checkout form below — add the recipient name, phone, "
            "and address, plus your name as sender, then tap Place order."
        ),
        "si": (
            "checkout පෝරමය පහළින් විවෘත කළා — ලබන්නාගේ නම, දුරකථනය, ලිපිනය "
            "සහ ඔබේ නම ඇතුළත් කර Place order තෝරන්න."
        ),
        "ta": (
            "checkout படிவம் கீழே திறக்கப்பட்டுள்ளது — பெறுநர் பெயர், தொலைபேசி, "
            "முகவரி மற்றும் உங்கள் பெயரை நிரப்பி Place order அழுத்துங்கள்."
        ),
    },
    "checkout_form_ready": {
        "en": (
            "I've filled in your checkout details on screen — review them and tap "
            "Place order to confirm."
        ),
        "si": "checkout විස්තර පිරවා ඇත — සමාලෝචනය කර Place order තෝරන්න.",
        "ta": "checkout விவரங்கள் நிரப்பப்பட்டுள்ளன — பார்த்து Place order அழுத்துங்கள்.",
    },
    "delivery_validated": {
        "en": (
            "Good news — delivery to {city} on {date} is available for LKR {rate} "
            "flat rate for your {count} item cart."
        ),
        "si": (
            "සතුටුදායකයි — {city} වෙත {date} දින බෙදාහැරීම LKR {rate} "
            "({count} අයිතම) සඳහා ලබා ගත හැක."
        ),
        "ta": (
            "நல்ல செய்தி — {city}க்கு {date} அன்று டெலிவரி LKR {rate} "
            "({count} பொருட்கள்) கிடைக்கிறது."
        ),
    },
    "empty_cart_checkout": {
        "en": (
            "Your cart is empty, so there's nothing to checkout yet. "
            "Tell me what gift you'd like to send and I'll find some options."
        ),
        "si": (
            "කරත්තය හිස් — checkout කිරීමට දෙයක් නැත. "
            "ඔබට යැවීමට අවශ්‍ත තෑග්ග කියන්න, මම විකල්ප සොයමි."
        ),
        "ta": (
            "கூடை காலியாக உள்ளது — checkout செய்ய எதுவும் இல்லை. "
            "எந்த பரிசு அனுப்ப வேண்டும் என்று சொல்லுங்கள், விருப்பங்களைக் காண்பிக்கிறேன்."
        ),
    },
    "products_found": {
        "en": (
            "I found {count} Kapruka options for '{query}' — they're on your screen now. "
            "Tap the one you like, or tell me which to add."
        ),
        "si": (
            "'{query}' සඳහා Kapruka විකල්ප {count}ක් — තිරයේ පෙන්වයි. "
            "එකක් තෝරන්න හෝ එකතු කිරීමට නම කියන්න."
        ),
        "ta": (
            "'{query}'க்கு Kapruka விருப்பங்கள் {count} — திரையில் உள்ளன. "
            "ஒன்றைத் தட்டுங்கள் அல்லது சேர்க்கச் சொல்லுங்கள்."
        ),
    },
}


def _lang(state: dict[str, Any] | None) -> str:
    code = str((state or {}).get("preferred_language") or "en").lower()
    return code if code in ("si", "ta") else "en"


def voice_msg(key: str, state: dict[str, Any] | None = None, **kwargs: Any) -> str:
    """Return a localized template; falls back to English."""
    lang = _lang(state)
    bucket = _MESSAGES.get(key, {})
    template = bucket.get(lang) or bucket.get("en") or key
    return template.format(**kwargs) if kwargs else template
