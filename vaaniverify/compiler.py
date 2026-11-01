"""Deterministic action-to-language compiler. No agent-controlled prose slots."""

import hashlib
import json

from .models import Action, DIRECTIONS, Language

TEMPLATES = {
    "en": {
        "READ_STATUS": "Read status only. No money leaves your account and no documents are shared.",
        "PAY": "Money leaves your account. Pay {amount} once to {recipient}.",
        "MANDATE": "Recurring debit. Pay up to {amount} {frequency} to {recipient}, for {installments} payments. Maximum total: {total}.",
        "SHARE": "Your documents leave your control. Share {documents} with {recipient} for {purpose}. Requested retention: {retention_days} days.",
        "CANCEL_MANDATE": "Cancel mandate {mandate_id}. This action does not create a new payment.",
        "WEEKLY": "every week", "MONTHLY": "every month",
        "driving_license": "driving licence", "degree_certificate": "degree certificate", "address_proof": "address proof",
        "employment": "employment", "education": "education", "identity_check": "identity verification",
    },
    "hinglish": {
        "READ_STATUS": "Sirf status dekhenge. Paisa NAHI katega aur documents share NAHI honge.",
        "PAY": "PAISA JAYEGA. Aapke account se {amount} ek baar {recipient} ko jayega.",
        "MANDATE": "BAAR-BAAR PAISA KATEGA. {recipient} ko {frequency} {amount} tak, {installments} payments. Kul seema: {total}.",
        "SHARE": "DOCUMENTS BAHAR JAYENGE. {documents}, {recipient} ko {purpose} ke liye. Rakhne ki maangi gayi avadhi: {retention_days} din.",
        "CANCEL_MANDATE": "Mandate {mandate_id} band hoga. Koi naya payment nahi hoga.",
        "WEEKLY": "har hafte", "MONTHLY": "har mahine",
        "driving_license": "driving licence", "degree_certificate": "degree certificate", "address_proof": "pate ka pramaan",
        "employment": "naukri", "education": "padhai", "identity_check": "pehchaan ki jaanch",
    },
    "hi": {
        "READ_STATUS": "सिर्फ स्थिति देखेंगे। खाते से पैसा नहीं कटेगा और दस्तावेज़ साझा नहीं होंगे।",
        "PAY": "पैसा जाएगा। आपके खाते से {amount} एक बार {recipient} को जाएंगे।",
        "MANDATE": "बार-बार पैसा कटेगा। {recipient} को {frequency} {amount} तक, कुल {installments} भुगतान। अधिकतम कुल राशि: {total}।",
        "SHARE": "दस्तावेज़ साझा होंगे। {documents}, {recipient} को {purpose} के लिए। रखने की मांगी गई अवधि: {retention_days} दिन।",
        "CANCEL_MANDATE": "मैंडेट {mandate_id} रद्द होगा। कोई नया भुगतान नहीं होगा।",
        "WEEKLY": "हर सप्ताह", "MONTHLY": "हर महीने",
        "driving_license": "ड्राइविंग लाइसेंस", "degree_certificate": "डिग्री प्रमाणपत्र", "address_proof": "पते का प्रमाण",
        "employment": "रोज़गार", "education": "शिक्षा", "identity_check": "पहचान की जांच",
    },
    "ta": {
        "READ_STATUS": "நிலையை மட்டும் பார்க்கும். பணம் கழிக்கப்படாது. ஆவணங்கள் பகிரப்படாது.",
        "PAY": "பணம் வெளியே செல்லும். உங்கள் கணக்கிலிருந்து {amount}, {recipient} க்கு ஒருமுறை செலுத்தப்படும்.",
        "MANDATE": "தொடர்ந்து பணம் கழிக்கப்படும். {recipient} க்கு {frequency} {amount} வரை, {installments} தவணைகள். மொத்த அதிகபட்சம்: {total}.",
        "SHARE": "ஆவணங்கள் பகிரப்படும். {documents}, {recipient} உடன் {purpose} நோக்கத்திற்காக. கோரப்பட்ட சேமிப்புக் காலம்: {retention_days} நாட்கள்.",
        "CANCEL_MANDATE": "{mandate_id} ஆணை ரத்து செய்யப்படும். புதிய பணம் செலுத்தப்படாது.",
        "WEEKLY": "ஒவ்வொரு வாரமும்", "MONTHLY": "ஒவ்வொரு மாதமும்",
        "driving_license": "ஓட்டுநர் உரிமம்", "degree_certificate": "பட்டச் சான்றிதழ்", "address_proof": "முகவரிச் சான்று",
        "employment": "வேலைவாய்ப்பு", "education": "கல்வி", "identity_check": "அடையாள சரிபார்ப்பு",
    },
}


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


TEMPLATE_HASH = digest(TEMPLATES)


def rupees(paise: int) -> str:
    # Integer arithmetic only: monetary values never pass through a float.
    whole, fraction = divmod(paise, 100)
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while head:
            groups.insert(0, head[-2:])
            head = head[:-2]
        digits = ",".join(groups + [tail])
    return f"₹{digits}" + (f".{fraction:02d}" if fraction else "")


def compile_action(action: Action, language: Language) -> dict:
    table = TEMPLATES[language]
    slots = action.model_dump(mode="json")
    slots.update(amount=rupees(action.amount_paise or 0),
                 total=rupees((action.amount_paise or 0) * (action.installments or 1)),
                 frequency=table.get(action.frequency, ""),
                 documents=", ".join(table[d] for d in action.documents),
                 purpose=table.get(action.purpose, ""))
    return {"text": table[action.operation].format(**slots), "language": language,
            "direction": DIRECTIONS[action.operation], "template_hash": TEMPLATE_HASH,
            "action_digest": digest(action.model_dump(mode="json")),
            "amount_display": rupees(action.amount_paise or 0),
            "maximum_total": rupees((action.amount_paise or 0) * (action.installments or 1)),
            "recipient": action.recipient, "operation": action.operation}
