import os
import json
import re
import unicodedata
import sqlite3
import requests
import secrets
import hashlib
import hmac
import smtplib
import base64
import urllib.parse
import io
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional, List, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from openai import OpenAI
from pydantic import BaseModel


# =========================
# CONFIGURAZIONE AMBIENTE
# =========================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "noreply@careercoach.local")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "30"))
OAUTH_REDIRECT_BASE_URL = os.getenv("OAUTH_REDIRECT_BASE_URL", "http://localhost:8000")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")
APPLE_CLIENT_SECRET = os.getenv("APPLE_CLIENT_SECRET")
APPLE_REDIRECT_URI = os.getenv("APPLE_REDIRECT_URI")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

if not GROQ_API_KEY:
    raise RuntimeError("Manca GROQ_API_KEY nel file .env")

if not TAVILY_API_KEY:
    raise RuntimeError("Manca TAVILY_API_KEY nel file .env")


groq_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    timeout=30.0
)


# =========================
# APP FASTAPI
# =========================

app = FastAPI(title="CareerCoach API - Interview Gym")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# DATABASE SQLITE
# =========================

DB_NAME = "careercoach.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def add_column_if_not_exists(cursor, table_name: str, column_name: str, column_sql: str):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [row[1] for row in cursor.fetchall()]

    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        education TEXT,
        target_role TEXT,
        sector TEXT,
        experience_level TEXT,
        interview_language TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interview_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        interview_type TEXT,
        difficulty TEXT,
        company TEXT,
        question_mode TEXT,
        total_score INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        category TEXT,
        difficulty TEXT,
        company TEXT,
        question_mode TEXT,
        sources_json TEXT,
        FOREIGN KEY(session_id) REFERENCES interview_sessions(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        user_answer TEXT NOT NULL,
        clarity_score INTEGER,
        completeness_score INTEGER,
        relevance_score INTEGER,
        professionalism_score INTEGER,
        synthesis_score INTEGER,
        speaking_score INTEGER,
        total_score INTEGER,
        feedback TEXT,
        improved_answer TEXT,
        speaking_feedback TEXT,
        solution_explanation TEXT,
        speech_metrics_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(question_id) REFERENCES questions(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS web_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT UNIQUE,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS question_web_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        source_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(question_id) REFERENCES questions(id),
        FOREIGN KEY(source_id) REFERENCES web_sources(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS oauth_states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        state TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    add_column_if_not_exists(cursor, "users", "password_hash", "TEXT")
    add_column_if_not_exists(cursor, "users", "phone", "TEXT")
    add_column_if_not_exists(cursor, "users", "email_verified", "INTEGER DEFAULT 0")
    add_column_if_not_exists(cursor, "users", "email_verification_token", "TEXT")
    add_column_if_not_exists(cursor, "users", "email_verification_expires_at", "TIMESTAMP")
    add_column_if_not_exists(cursor, "users", "password_reset_token", "TEXT")
    add_column_if_not_exists(cursor, "users", "password_reset_expires_at", "TIMESTAMP")
    add_column_if_not_exists(cursor, "users", "created_at", "TIMESTAMP")
    add_column_if_not_exists(cursor, "users", "last_login_at", "TIMESTAMP")
    add_column_if_not_exists(cursor, "users", "auth_provider", "TEXT")
    add_column_if_not_exists(cursor, "users", "provider_user_id", "TEXT")
    add_column_if_not_exists(cursor, "users", "cv_filename", "TEXT")
    add_column_if_not_exists(cursor, "users", "cv_content_type", "TEXT")
    add_column_if_not_exists(cursor, "users", "cv_size", "INTEGER")
    add_column_if_not_exists(cursor, "users", "cv_text", "TEXT")
    add_column_if_not_exists(cursor, "users", "cv_file_base64", "TEXT")
    add_column_if_not_exists(cursor, "users", "cv_uploaded_at", "TIMESTAMP")
    add_column_if_not_exists(cursor, "users", "linkedin_url", "TEXT")
    add_column_if_not_exists(cursor, "users", "portfolio_url", "TEXT")
    add_column_if_not_exists(cursor, "users", "instagram_handle", "TEXT")
    add_column_if_not_exists(cursor, "users", "digital_analysis_json", "TEXT")

    add_column_if_not_exists(cursor, "interview_sessions", "company", "TEXT")
    add_column_if_not_exists(cursor, "interview_sessions", "question_mode", "TEXT")

    add_column_if_not_exists(cursor, "questions", "company", "TEXT")
    add_column_if_not_exists(cursor, "questions", "question_mode", "TEXT")
    add_column_if_not_exists(cursor, "questions", "sources_json", "TEXT")

    add_column_if_not_exists(cursor, "answers", "speaking_score", "INTEGER")
    add_column_if_not_exists(cursor, "answers", "speaking_feedback", "TEXT")
    add_column_if_not_exists(cursor, "answers", "solution_explanation", "TEXT")
    add_column_if_not_exists(cursor, "answers", "speech_metrics_json", "TEXT")

    conn.commit()
    conn.close()


init_db()


# =========================
# MODELLI PYDANTIC
# =========================

class UserCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    education: str
    target_role: str
    sector: str
    experience_level: str
    interview_language: str = "Italiano"


class UserUpdate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    education: str
    target_role: str
    sector: str
    experience_level: str
    interview_language: str = "Italiano"


class UserCvUpload(BaseModel):
    filename: str
    content_type: Optional[str] = None
    size: int
    text: Optional[str] = None
    file_base64: Optional[str] = None


class DigitalPresenceUpdate(BaseModel):
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    instagram_handle: Optional[str] = None
    linkedin_connected: bool = False


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    identifier: str
    password: str


class TokenRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    identifier: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class GenerateQuestionRequest(BaseModel):
    user_id: int
    interview_type: str
    difficulty: str = "intermedio"
    company: Optional[str] = "Generica"
    question_mode: Optional[str] = "web"


class SpeechMetrics(BaseModel):
    duration_seconds: Optional[float] = None
    words_count: Optional[int] = None
    words_per_minute: Optional[float] = None
    filler_words_count: Optional[int] = None
    filler_words: Optional[List[str]] = None


class EvaluateAnswerRequest(BaseModel):
    question_id: int
    answer: str
    speech_metrics: Optional[SpeechMetrics] = None


class SearchInterviewQuestionsRequest(BaseModel):
    company: str
    role: str
    interview_type: str
    language: str = "Italiano"


# =========================
# FUNZIONI AUTH / EMAIL
# =========================

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
BLOCKED_EMAIL_DOMAINS = {
    "example.com",
    "example.it",
    "test.com",
    "test.it",
    "email.com",
    "mailinator.com",
    "tempmail.com",
    "10minutemail.com",
}


def utc_now() -> datetime:
    return datetime.utcnow()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None

    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    return cleaned or None


def validate_email_address(email: str) -> str:
    normalized = normalize_email(email)
    domain = normalized.split("@")[-1] if "@" in normalized else ""
    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""

    if (
        not EMAIL_PATTERN.match(normalized)
        or len(tld) < 2
        or domain in BLOCKED_EMAIL_DOMAINS
        or ".." in normalized
    ):
        raise HTTPException(status_code=400, detail="Inserisci un indirizzo email reale e valido.")

    return normalized


def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="La password deve avere almeno 8 caratteri.")

    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="La password deve includere almeno una lettera e un numero.")


def validate_phone(phone: Optional[str]) -> Optional[str]:
    normalized = normalize_phone(phone)
    if not normalized:
        return None

    digits = re.sub(r"\D", "", normalized)
    if len(digits) < 8 or len(digits) > 15:
        raise HTTPException(status_code=400, detail="Inserisci un numero di cellulare valido.")

    return normalized


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    if not stored_hash:
        return False

    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except ValueError:
        return False


def make_token() -> str:
    return secrets.token_urlsafe(32)


def make_frontend_link(kind: str, token: str) -> str:
    return f"{FRONTEND_URL}/?{kind}={token}"


def normalize_oauth_provider(provider: str) -> str:
    return "google" if provider == "gmail" else provider.strip().lower()


def make_oauth_callback_url(provider: str) -> str:
    provider = normalize_oauth_provider(provider)
    provider_redirects = {
        "google": GOOGLE_REDIRECT_URI,
        "apple": APPLE_REDIRECT_URI,
        "linkedin": LINKEDIN_REDIRECT_URI,
    }

    return provider_redirects.get(provider) or f"{OAUTH_REDIRECT_BASE_URL}/auth/oauth/{provider}/callback"


def make_frontend_oauth_link(token: str) -> str:
    return f"{FRONTEND_URL}/?oauth_token={token}"


def decode_jwt_payload(token: str) -> Dict:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
    except Exception:
        return {}


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        return False

    try:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = SMTP_FROM
        message["To"] = to_email
        message.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)

        return True
    except Exception as exc:
        print(f"Invio email non riuscito: {exc}")
        return False


def user_to_response(row):
    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "education": row[3],
        "target_role": row[4],
        "sector": row[5],
        "experience_level": row[6],
        "interview_language": row[7],
        "phone": row[8],
        "email_verified": bool(row[9]),
        "cv_filename": row[10],
        "cv_uploaded": bool(row[10]),
        "cv_text": row[13] or "",
        "cv_uploaded_at": row[15],
        "linkedin_url": row[16],
        "portfolio_url": row[17],
        "instagram_handle": row[18],
        "digital_analysis": json.loads(row[19]) if row[19] else None,
        "auth_provider": row[20],
    }


def create_session(cursor, user_id: int) -> str:
    token = make_token()
    expires_at = utc_now() + timedelta(days=SESSION_DAYS)
    cursor.execute("""
    INSERT INTO user_sessions (user_id, token, expires_at)
    VALUES (?, ?, ?)
    """, (user_id, token, expires_at.isoformat()))
    cursor.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    return token


def fetch_user_by_id(cursor, user_id: int):
    cursor.execute("""
    SELECT
        id,
        name,
        email,
        education,
        target_role,
        sector,
        experience_level,
        interview_language,
        phone,
        email_verified,
        cv_filename,
        cv_content_type,
        cv_size,
        cv_text,
        cv_file_base64,
        cv_uploaded_at,
        linkedin_url,
        portfolio_url,
        instagram_handle,
        digital_analysis_json,
        auth_provider
    FROM users
    WHERE id = ?
    """, (user_id,))
    return cursor.fetchone()


def get_oauth_config(provider: str) -> Dict:
    provider = normalize_oauth_provider(provider)

    configs = {
        "google": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": make_oauth_callback_url("google"),
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "scope": "openid email profile",
        },
        "apple": {
            "client_id": APPLE_CLIENT_ID,
            "client_secret": APPLE_CLIENT_SECRET,
            "redirect_uri": make_oauth_callback_url("apple"),
            "auth_url": "https://appleid.apple.com/auth/authorize",
            "token_url": "https://appleid.apple.com/auth/token",
            "userinfo_url": None,
            "scope": "name email",
        },
        "linkedin": {
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET,
            "redirect_uri": make_oauth_callback_url("linkedin"),
            "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
            "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
            "userinfo_url": "https://api.linkedin.com/v2/userinfo",
            "scope": "openid profile email",
            "setup_hint": (
                "In LinkedIn Developers abilita il prodotto 'Sign In with LinkedIn using OpenID Connect' "
                "e registra esattamente il redirect URI configurato nel backend."
            ),
        },
    }

    if provider not in configs:
        raise HTTPException(status_code=404, detail="Provider non supportato.")

    config = configs[provider]
    if not config["client_id"] or not config["client_secret"]:
        raise HTTPException(
            status_code=400,
            detail=f"Configura {provider.upper()}_CLIENT_ID e {provider.upper()}_CLIENT_SECRET nel file .env.",
        )

    return {"provider": provider, **config}


def create_oauth_state(cursor, provider: str) -> str:
    state = make_token()
    expires_at = utc_now() + timedelta(minutes=10)
    cursor.execute("""
    INSERT INTO oauth_states (provider, state, expires_at)
    VALUES (?, ?, ?)
    """, (provider, state, expires_at.isoformat()))
    return state


def build_oauth_authorization_url(provider: str, state: str) -> str:
    config = get_oauth_config(provider)
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": config["scope"],
        "state": state,
    }

    if config["provider"] == "apple":
        params["response_mode"] = "query"

    return f"{config['auth_url']}?{urllib.parse.urlencode(params)}"


def consume_oauth_state(cursor, provider: str, state: str):
    cursor.execute("""
    SELECT expires_at
    FROM oauth_states
    WHERE provider = ? AND state = ?
    """, (provider, state))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=400, detail="Sessione OAuth non valida.")

    cursor.execute("DELETE FROM oauth_states WHERE state = ?", (state,))

    if datetime.fromisoformat(row[0]) < utc_now():
        raise HTTPException(status_code=400, detail="Sessione OAuth scaduta.")


def fetch_oauth_profile(provider: str, code: str) -> Dict:
    config = get_oauth_config(provider)
    provider = config["provider"]
    token_response = requests.post(
        config["token_url"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )

    if token_response.status_code >= 400:
        provider_hint = config.get("setup_hint", "Controlla client id, client secret e redirect URI del provider.")
        raise HTTPException(
            status_code=400,
            detail=(
                f"Accesso {provider} non riuscito durante lo scambio del codice. "
                f"{provider_hint} Dettaglio provider: {token_response.text[:300]}"
            ),
        )

    token_data = token_response.json()

    if provider == "apple":
        profile = decode_jwt_payload(token_data.get("id_token", ""))
    else:
        userinfo_response = requests.get(
            config["userinfo_url"],
            headers={"Authorization": f"Bearer {token_data.get('access_token')}"},
            timeout=15,
        )
        if userinfo_response.status_code >= 400:
            provider_hint = config.get("setup_hint", "Controlla permessi e scope del provider.")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Impossibile leggere il profilo {provider}. "
                    f"{provider_hint} Dettaglio provider: {userinfo_response.text[:300]}"
                ),
            )
        profile = userinfo_response.json()

    email = profile.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Il provider non ha restituito un indirizzo email.")

    name = (
        profile.get("name")
        or " ".join(part for part in [profile.get("given_name"), profile.get("family_name")] if part).strip()
        or email.split("@")[0]
    )

    return {
        "provider_user_id": str(profile.get("sub") or profile.get("id") or email),
        "email": validate_email_address(email),
        "name": name,
    }


def find_or_create_oauth_user(cursor, provider: str, profile: Dict) -> int:
    cursor.execute("""
    SELECT id
    FROM users
    WHERE auth_provider = ? AND provider_user_id = ?
    """, (provider, profile["provider_user_id"]))
    provider_row = cursor.fetchone()
    if provider_row:
        return provider_row[0]

    cursor.execute("SELECT id FROM users WHERE lower(email) = lower(?)", (profile["email"],))
    email_row = cursor.fetchone()
    if email_row:
        cursor.execute("""
        UPDATE users
        SET auth_provider = ?,
            provider_user_id = ?,
            email_verified = 1
        WHERE id = ?
        """, (provider, profile["provider_user_id"], email_row[0]))
        return email_row[0]

    cursor.execute("""
    INSERT INTO users (
        name,
        email,
        email_verified,
        auth_provider,
        provider_user_id,
        education,
        target_role,
        sector,
        experience_level,
        interview_language
    )
    VALUES (?, ?, 1, ?, ?, '', '', '', 'Junior', 'Italiano')
    """, (
        profile["name"],
        profile["email"],
        provider,
        profile["provider_user_id"],
    ))
    return cursor.lastrowid


# =========================
# FUNZIONI AI / WEB SEARCH
# =========================

def call_groq(prompt: str, temperature: float = 0.7, max_tokens: int = 1000) -> str:
    try:
        print("Chiamata Groq avviata...")

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un assistente esperto nella preparazione ai colloqui di lavoro. "
                        "Aiuti candidati junior, studenti e neolaureati a prepararsi "
                        "in modo realistico, concreto e pratico."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=25
        )

        print("Chiamata Groq completata.")
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Errore Groq: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante la chiamata a GroqCloud: {str(e)}"
        )


def extract_json(text: str):
    text = text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1

        if start != -1 and end != -1:
            return json.loads(text[start:end])

        raise ValueError(f"JSON non valido restituito dal modello: {text}")


CV_SECTION_KEYWORDS = {
    "contatti": [
        "contatti", "telefono", "email", "e-mail", "linkedin", "indirizzo",
        "numero", "cellulare", "mobile", "phone"
    ],
    "profilo personale": [
        "profilo personale", "profilo professionale", "personal profile",
        "chi sono", "summary", "about me", "presentazione", "obiettivo",
        "career objective"
    ],
    "esperienze professionali": [
        "esperienze professionali", "esperienza professionale", "esperienza",
        "esperienze", "experience", "work experience", "employment", "lavoro",
        "azienda", "tirocinio", "stage", "internship", "ruolo", "position"
    ],
    "formazione": [
        "formazione", "formazione accademica", "istruzione", "education",
        "universita", "università", "university", "laurea", "laurea magistrale",
        "laurea triennale", "diploma", "liceo", "master", "degree"
    ],
    "competenze": [
        "competenze", "competenze tecniche", "skills", "technical skills",
        "hard skills", "soft skills", "capacita", "capacità", "tecnologie",
        "linguaggi", "software", "tools", "python", "sql", "java", "c++",
        "machine learning", " ai ", " ml "
    ],
    "lingue": ["lingue", "languages", "italiano", "inglese", "francese", "spagnolo"],
    "certificazioni": [
        "certificazioni", "certifications", "certificate", "attestati",
        "abilitazioni"
    ],
    "progetti": ["progetti", "projects", "project work", "tesi", "tirocinio"],
    "linkedin": ["linkedin", "linkedin.com"],
    "github": ["github", "github.com"],
    "portfolio": ["portfolio", "website", "sito personale", "behance", "dribbble"],
}


def decode_text_bytes(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def clean_extracted_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_for_cv_detection(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return f" {normalized} "


def extract_pdf_with_pymupdf(file_bytes: bytes) -> str:
    text_parts = []

    try:
        import fitz

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            page_text = page.get_text("text")
            if page_text:
                text_parts.append(page_text)
        doc.close()
        return "\n".join(text_parts).strip()
    except Exception as exc:
        print("Errore PyMuPDF:", exc)
        return ""


def extract_pdf_with_pypdf(file_bytes: bytes) -> str:
    text_parts = []

    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts).strip()
    except Exception as exc:
        print("Errore pypdf:", exc)
        return ""


def extract_text_from_file_bytes(file_bytes: bytes, filename: str) -> tuple[str, str]:
    lower_filename = filename.lower()

    if lower_filename.endswith(".pdf"):
        text = extract_pdf_with_pymupdf(file_bytes)
        if len(text.strip()) >= 50:
            return text, "pymupdf"

        text = extract_pdf_with_pypdf(file_bytes)
        if len(text.strip()) >= 50:
            return text, "pypdf"

        return text, "pdf_failed_or_scanned"

    if lower_filename.endswith(".docx"):
        try:
            from docx import Document

            document = Document(io.BytesIO(file_bytes))
            text_parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
            text_parts.extend(
                cell.text
                for table in document.tables
                for row in table.rows
                for cell in row.cells
                if cell.text
            )
            return "\n".join(text_parts).strip(), "docx"
        except Exception as exc:
            print("Errore DOCX:", exc)
            return "", "failed"

    if lower_filename.endswith(".txt"):
        return decode_text_bytes(file_bytes).strip(), "txt"

    return "", "failed"


def extract_text_with_method(file_bytes: bytes, filename: str) -> Dict:
    text, method = extract_text_from_file_bytes(file_bytes, filename)
    return {"text": text, "method": method, "errors": []}


def extract_text_from_cv_upload(filename: str, content: bytes) -> str:
    text, _method = extract_text_from_file_bytes(content, filename)
    return text


def analyze_cv_heuristics(text: str) -> Dict:
    normalized = normalize_for_cv_detection(text)
    detected_sections = []
    signals = []

    has_email = bool(re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", normalized))
    has_phone = bool(re.search(r"(?:\+?\d[\s().-]*){8,}", normalized))
    has_name_like_line = any(
        2 <= len(re.findall(r"\b[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ']+\b", line)) <= 4
        for line in text.splitlines()[:8]
    )

    if has_email:
        detected_sections.append("email")
        detected_sections.append("contatti")
        signals.append("email")
        signals.append("contatti")
    if has_phone or "numero" in normalized:
        detected_sections.append("telefono")
        detected_sections.append("contatti")
        signals.append("telefono")
        signals.append("contatti")
    if has_name_like_line:
        signals.append("nome e cognome")

    for section, keywords in CV_SECTION_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            detected_sections.append(section)
            signals.append(section)

    unique_sections = sorted(set(detected_sections))
    unique_signals = sorted(set(signals))

    score = 0
    score += 15 if "email" in unique_signals else 0
    score += 15 if "telefono" in unique_signals else 0
    score += 10 if "linkedin" in unique_signals else 0
    score += 20 if "esperienze professionali" in unique_signals else 0
    score += 20 if "formazione" in unique_signals else 0
    score += 20 if "competenze" in unique_signals else 0
    score += 10 if "lingue" in unique_signals else 0

    optional_sections = {"certificazioni", "progetti", "github", "portfolio"}
    score += 10 if optional_sections.intersection(unique_signals) else 0
    score += 10 if "profilo personale" in unique_signals else 0
    score = min(score, 100)

    reason = "Il documento e leggibile, ma non contiene abbastanza elementi tipici di un curriculum."
    if score >= 45:
        reason = (
            "Il documento contiene elementi tipici di un CV: "
            f"{', '.join(unique_sections[:8])}."
        )
    elif 35 <= score <= 49 and ("email" in unique_signals or "telefono" in unique_signals):
        reason = (
            "Il documento contiene alcuni elementi tipici di un CV e almeno un contatto: "
            f"{', '.join(unique_sections[:8])}."
        )

    return {
        "score": score,
        "confidence": score,
        "detected_sections": unique_sections,
        "signals": unique_signals,
        "reason": reason,
    }


def classify_cv_with_llm(text: str) -> Optional[Dict]:
    prompt = f"""
Devi stabilire se il documento seguente e un curriculum vitae.

Classifica il documento come:
- CV valido
- probabilmente CV
- non CV

Restituisci SOLO JSON valido con questa struttura:
{{
  "is_cv": true,
  "confidence": 0,
  "reason": "spiegazione breve",
  "detected_sections": []
}}

Testo estratto dal documento:
{text[:6000]}
"""

    try:
        raw_output = call_groq(prompt, temperature=0.1, max_tokens=500)
        result = extract_json(raw_output)
        return {
            "is_cv": bool(result.get("is_cv")),
            "confidence": clamp_score(result.get("confidence", 0)),
            "reason": str(result.get("reason", "")).strip(),
            "detected_sections": result.get("detected_sections", []),
        }
    except Exception as exc:
        print(f"Classificazione LLM CV non disponibile: {exc}")
        return None


def extract_questions_list(text: str) -> List[str]:
    """
    Estrae una lista pulita di domande dal testo restituito dal modello.
    Gestisce:
    - JSON corretto {"questions": [...]}
    - lista JSON [...]
    - testo numerato
    - risposte con frase introduttiva
    """

    text = text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()

    questions = []

    try:
        data = json.loads(text)

        if isinstance(data, dict) and "questions" in data:
            questions = data["questions"]
        elif isinstance(data, list):
            questions = data

    except Exception:
        questions = []

    if not questions:
        lines = text.split("\n")

        for line in lines:
            line = line.strip()

            if not line:
                continue

            cleaned = line.lstrip("-• ")
            cleaned = cleaned.strip()

            parts = cleaned.split(maxsplit=1)
            if parts:
                first = parts[0].replace(".", "").replace(")", "")
                if first.isdigit() and len(parts) > 1:
                    cleaned = parts[1].strip()

            lower = cleaned.lower()

            intro_phrases = [
                "ecco le 10 domande",
                "ecco dieci domande",
                "di seguito",
                "queste sono",
                "certamente",
                "ecco una lista",
                "ecco le domande"
            ]

            if any(phrase in lower for phrase in intro_phrases):
                continue

            if "?" in cleaned and len(cleaned) > 15:
                questions.append(cleaned)

    clean_questions = []

    for question in questions:
        if not isinstance(question, str):
            continue

        q = question.strip()
        lower_q = q.lower()

        if any(phrase in lower_q for phrase in [
            "ecco le 10 domande",
            "ecco dieci domande",
            "di seguito",
            "queste sono",
            "ecco una lista",
            "ecco le domande"
        ]):
            continue

        if len(q) > 15 and "?" in q:
            clean_questions.append(q)

    return clean_questions[:10]


def clamp_score(value):
    try:
        value = int(value)
    except Exception:
        value = 0

    return max(0, min(100, value))


def compute_total_score(
    clarity_score,
    completeness_score,
    relevance_score,
    professionalism_score,
    synthesis_score,
    speaking_score
):
    scores = [
        clarity_score,
        completeness_score,
        relevance_score,
        professionalism_score,
        synthesis_score
    ]

    if speaking_score > 0:
        scores.append(speaking_score)

    return round(sum(scores) / len(scores))


def build_speaking_feedback_from_metrics(metrics: SpeechMetrics) -> str:
    """
    Costruisce un feedback testuale sul parlato usando le metriche ricevute dal frontend.
    Non serve mostrarle a schermo: servono solo per produrre una valutazione più utile.
    """

    duration = metrics.duration_seconds or 0
    words = metrics.words_count or 0
    wpm = metrics.words_per_minute or 0
    fillers = metrics.filler_words_count or 0

    if words <= 0:
        return (
            "Il modo di parlare non è valutabile perché la risposta non contiene parole trascritte "
            "in modo sufficiente."
        )

    if wpm < 80:
        ritmo = (
            "Il ritmo risulta piuttosto lento: in un colloquio può trasmettere esitazione "
            "o poca sicurezza, quindi conviene allenarsi a parlare in modo leggermente più fluido."
        )
    elif wpm <= 160:
        ritmo = (
            "Il ritmo è complessivamente adeguato per un colloquio: permette a chi ascolta "
            "di seguire il discorso senza difficoltà."
        )
    else:
        ritmo = (
            "Il ritmo è abbastanza veloce: conviene rallentare leggermente per risultare più chiara, "
            "ordinata e sicura."
        )

    if fillers == 0:
        riempitivi = (
            "Non emergono parole riempitive rilevanti, quindi il discorso appare abbastanza pulito."
        )
    elif fillers <= 2:
        riempitivi = (
            "Sono presenti poche parole riempitive: non compromettono la risposta, ma si può ancora "
            "migliorare la fluidità."
        )
    else:
        riempitivi = (
            "Sono presenti diverse parole riempitive: questo può rendere il discorso meno sicuro "
            "e meno professionale."
        )

    if duration < 10 or words < 15:
        struttura = (
            "La risposta è breve: per un colloquio sarebbe utile sviluppare meglio il discorso "
            "con un esempio concreto o una motivazione più chiara."
        )
    else:
        struttura = (
            "La risposta ha una durata sufficiente per essere valutata anche dal punto di vista espositivo."
        )

    return f"{ritmo} {riempitivi} {struttura}"


# =========================
# FILTRO RISPOSTE NON VALIDE
# =========================

def normalize_answer_text(text: str) -> str:
    """
    Normalizza il testo per riconoscere meglio risposte non valide:
    - minuscole;
    - rimozione accenti;
    - rimozione punteggiatura;
    - spazi uniformi.
    """

    if not text:
        return ""

    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def get_zero_answer_reason(answer: str, question: str = "") -> Optional[str]:
    """
    Restituisce il motivo per cui una risposta deve prendere 0.
    Se la risposta è valutabile, restituisce None.

    Serve per bloccare prima dell'LLM risposte come:
    - "che criterio usi per valutarmi?";
    - "quanto mi dai?";
    - "qual è la risposta giusta?";
    - "boh", "non lo so";
    - testo casuale o troppo breve.
    """

    if not answer:
        return "Risposta vuota"

    original_text = answer.strip()
    text = normalize_answer_text(original_text)

    if len(text) < 3:
        return "Risposta troppo breve"

    zero_phrases = {
        "boh",
        "bo",
        "mah",
        "non lo so",
        "non so",
        "chi lo sa",
        "non saprei",
        "non ne ho idea",
        "nessuna idea",
        "non mi viene",
        "non mi viene in mente",
        "non voglio rispondere",
        "skip",
        "passo",
        "idk",
        "i don t know",
        "dont know",
        "no idea"
    }

    if text in zero_phrases:
        return "Risposta di rinuncia o assenza di contenuto"

    words = text.split()

    if len(words) < 3:
        return "Risposta troppo breve per essere valutata"

    for phrase in zero_phrases:
        if phrase in text and len(words) <= 8:
            return "Risposta di rinuncia o forte incertezza"

    meta_patterns = [
        r"\bche criterio\b.*\bvalut",
        r"\bche criteri\b.*\bvalut",
        r"\bquale criterio\b.*\bvalut",
        r"\bquali criteri\b.*\bvalut",
        r"\bcome\b.*\bvalut",
        r"\bcome mi valuti\b",
        r"\bquanto mi dai\b",
        r"\bquanto mi daresti\b",
        r"\bche punteggio\b",
        r"\bche voto\b",
        r"\bche giudizio\b",
        r"\bqual e la risposta corretta\b",
        r"\bqual e la risposta giusta\b",
        r"\bcosa dovrei rispondere\b",
        r"\bcosa devo rispondere\b",
        r"\bmi aiuti\b.*\brispondere\b",
        r"\bpuoi aiutarmi\b.*\brispondere\b",
        r"\bpuoi farmi un esempio\b",
        r"\bfammi un esempio\b",
        r"\bdammi la risposta\b",
        r"\bsuggeriscimi\b.*\brisposta\b",
        r"\bpuoi spiegarmi\b.*\bdomanda\b",
        r"\bnon ho capito\b.*\bdomanda\b",
        r"\bcome funziona\b.*\bvalut",
        r"\bcome funziona\b.*\bsistema\b",
        r"\bcome funziona\b.*\bcodice\b",
        r"\bcome e costruito\b.*\bcodice\b",
        r"\blogica\b.*\bprogetto\b",
        r"\bsistema di valutazione\b",
        r"\bcriteri di valutazione\b"
    ]

    for pattern in meta_patterns:
        if re.search(pattern, text):
            return (
                "Risposta non valida: il candidato fa una domanda sul sistema, "
                "sulla valutazione o su cosa rispondere"
            )

    question_words = [
        "che",
        "come",
        "quanto",
        "quale",
        "quali",
        "cosa",
        "perche",
        "puoi",
        "potresti",
        "sapresti",
        "mi"
    ]

    if original_text.endswith("?") and words and words[0] in question_words:
        return "Risposta non valida: il candidato fa una domanda invece di rispondere"

    irrelevant_short_answers = {
        "ciao",
        "ok",
        "okay",
        "va bene",
        "bene",
        "male",
        "si",
        "sì",
        "no",
        "forse",
        "niente",
        "nulla",
        "tutto bene",
        "mi piace",
        "non mi piace",
        "dipende"
    }

    if text in irrelevant_short_answers:
        return "Risposta troppo generica o non pertinente"

    vowels = "aeiou"
    weird_words = 0

    for word in words:
        clean_word = "".join(ch for ch in word if ch.isalpha())

        if not clean_word:
            weird_words += 1
            continue

        if len(clean_word) >= 5 and not any(v in clean_word for v in vowels):
            weird_words += 1

        consecutive_consonants = 0
        max_consecutive_consonants = 0

        for ch in clean_word:
            if ch.isalpha() and ch not in vowels:
                consecutive_consonants += 1
                max_consecutive_consonants = max(max_consecutive_consonants, consecutive_consonants)
            else:
                consecutive_consonants = 0

        if max_consecutive_consonants >= 5:
            weird_words += 1

    weird_ratio = weird_words / len(words)

    if weird_ratio >= 0.5:
        return "Risposta indecifrabile o composta da testo casuale"

    letters = sum(1 for ch in text if ch.isalpha())
    total = len(text)

    if total > 0 and letters / total < 0.45:
        return "Risposta non valutabile perché contiene troppo poco testo significativo"

    return None


def is_zero_answer(answer: str, question: str = "") -> bool:
    return get_zero_answer_reason(answer, question) is not None


def build_zero_feedback(
    reason: str = "Risposta non valutabile",
    question: str = "",
    interview_type: str = ""
):
    """
    Feedback standard per risposte indecifrabili, non pertinenti o prive di contenuto.
    """

    if interview_type == "logica":
        improved_answer = (
            "La risposta non è valutabile. Per una domanda di logica, una risposta corretta dovrebbe "
            "spiegare il ragionamento passo dopo passo, chiarendo le ipotesi fatte, i passaggi intermedi "
            "e la conclusione. Non basta dare un numero o dire 'non lo so'."
        )
        solution_explanation = (
            f"Per risolvere questa domanda bisogna partire dal testo: '{question}'. "
            "Individua prima cosa viene chiesto, poi elenca le ipotesi, costruisci un ragionamento "
            "progressivo e arriva a una conclusione motivata. Nelle domande di stima non conta il numero "
            "esatto, ma la qualità del ragionamento."
        )
    else:
        improved_answer = (
            f"Una risposta efficace alla domanda '{question}' dovrebbe essere chiara, pertinente e strutturata. "
            "Puoi iniziare rispondendo direttamente alla domanda, poi aggiungere un esempio concreto o una "
            "motivazione collegata al ruolo e concludere spiegando cosa potresti portare all'azienda."
        )
        solution_explanation = ""

    return {
        "clarity_score": 0,
        "completeness_score": 0,
        "relevance_score": 0,
        "professionalism_score": 0,
        "synthesis_score": 0,
        "speaking_score": 0,
        "total_score": 0,
        "feedback": (
            f"{reason}. La risposta non può essere considerata valida in un colloquio, "
            "perché non fornisce contenuto utile, non risponde alla domanda oppure risulta "
            "troppo vaga/indecifrabile."
        ),
        "improved_answer": improved_answer,
        "speaking_feedback": (
            "Il modo di parlare non è valutabile perché il contenuto della risposta non è valido."
        ),
        "solution_explanation": solution_explanation
    }


def get_speech_metrics_json(metrics: Optional[SpeechMetrics]) -> Optional[str]:
    if not metrics:
        return None

    try:
        return metrics.model_dump_json()
    except Exception:
        return metrics.json()


def save_answer_result(
    cursor,
    question_id: int,
    user_answer: str,
    result: Dict,
    speech_metrics_json: Optional[str]
):
    cursor.execute("""
    INSERT INTO answers (
        question_id,
        user_answer,
        clarity_score,
        completeness_score,
        relevance_score,
        professionalism_score,
        synthesis_score,
        speaking_score,
        total_score,
        feedback,
        improved_answer,
        speaking_feedback,
        solution_explanation,
        speech_metrics_json
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        question_id,
        user_answer,
        result["clarity_score"],
        result["completeness_score"],
        result["relevance_score"],
        result["professionalism_score"],
        result["synthesis_score"],
        result["speaking_score"],
        result["total_score"],
        result["feedback"],
        result["improved_answer"],
        result["speaking_feedback"],
        result["solution_explanation"],
        speech_metrics_json
    ))


def build_search_query(company: str, role: str, interview_type: str, language: str) -> str:
    company = company.strip()
    role = role.strip()
    interview_type = interview_type.strip()

    if language.lower().startswith("ingles"):
        if interview_type == "conoscitive_motivazionali":
            return (
                f"{company} interview questions motivation behavioral cultural fit "
                f"tell me about yourself why do you want to work here goals teamwork"
            )

        if interview_type == "tecniche":
            return (
                f"{company} {role} technical interview questions skills assessment "
                f"role specific interview questions"
            )

        if interview_type == "logica":
            return (
                f"{company} logic interview questions brain teasers reasoning puzzles "
                f"problem solving interview questions"
            )

        return f"{company} {role} interview questions"

    if interview_type == "conoscitive_motivazionali":
        return (
            f"{company} domande colloquio motivazionale conoscitivo "
            f"parlami di te obiettivi perché vuoi lavorare qui lavoro di gruppo "
            f"cosa sai dell'azienda"
        )

    if interview_type == "tecniche":
        return (
            f"{company} {role} domande colloquio tecnico competenze "
            f"domande tecniche ruolo selezione candidato"
        )

    if interview_type == "logica":
        return (
            f"{company} domande colloquio logica ragionamento indovinelli "
            f"brain teaser problem solving trabocchetto stima"
        )

    return f"{company} {role} domande colloquio"


def search_web_interview_questions(
    company: str,
    role: str,
    interview_type: str,
    language: str = "Italiano"
) -> List[Dict[str, str]]:
    query = build_search_query(company, role, interview_type, language)

    try:
        print(f"Ricerca Tavily avviata: {query}")

        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": 3,
                "include_answer": False,
                "include_raw_content": False
            },
            timeout=10
        )

        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        clean_results = []

        for item in results:
            clean_results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "")
            })

        print(f"Ricerca Tavily completata. Fonti trovate: {len(clean_results)}")
        return clean_results

    except Exception as e:
        print(f"Errore Tavily, continuo senza fonti web: {e}")
        return []


def sources_to_prompt(sources: List[Dict[str, str]]) -> str:
    if not sources:
        return "Nessuna fonte web trovata."

    text = ""

    for index, source in enumerate(sources, start=1):
        text += f"""
Fonte {index}
Titolo: {source.get("title", "")}
URL: {source.get("url", "")}
Estratto: {source.get("content", "")}
"""

    return text


def normalize_instagram_handle(handle: Optional[str]) -> str:
    if not handle:
        return ""

    cleaned = handle.strip()
    cleaned = cleaned.replace("https://www.instagram.com/", "")
    cleaned = cleaned.replace("https://instagram.com/", "")
    cleaned = cleaned.split("?")[0].strip("/")
    cleaned = cleaned.lstrip("@")
    return cleaned


def normalize_public_profile_url(url: Optional[str]) -> str:
    if not url:
        return ""

    cleaned = url.strip()
    if cleaned and not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned.rstrip("/")


def profile_path(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(normalize_public_profile_url(url))
        return parsed.path.strip("/").lower()
    except Exception:
        return ""


def search_public_profile_signals(user: Dict, digital_presence: DigitalPresenceUpdate) -> List[Dict[str, str]]:
    search_terms = []
    linkedin_url = normalize_public_profile_url(digital_presence.linkedin_url)
    portfolio_url = normalize_public_profile_url(digital_presence.portfolio_url)
    linkedin_path = profile_path(linkedin_url)
    instagram_handle = normalize_instagram_handle(digital_presence.instagram_handle)

    if linkedin_url:
        search_terms.append(linkedin_url)
    if portfolio_url:
        search_terms.append(portfolio_url)

    sources = []
    seen_urls = set()

    if instagram_handle:
        instagram_url = f"https://www.instagram.com/{instagram_handle}/"
        sources.append({
            "title": f"Instagram @{instagram_handle}",
            "url": instagram_url,
            "content": "Profilo Instagram indicato direttamente dal candidato. Verificare foto, bio e contenuti pubblici rispetto al posizionamento professionale.",
        })
        seen_urls.add(instagram_url)

    for query in search_terms[:3]:
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 3,
                    "include_answer": False,
                    "include_raw_content": False,
                },
                timeout=10,
            )
            response.raise_for_status()
            for item in response.json().get("results", []):
                url = item.get("url", "")
                title = item.get("title", "")
                content = item.get("content", "")
                normalized_url = normalize_public_profile_url(url)
                if "linkedin.com" in normalized_url:
                    if not linkedin_path:
                        continue
                    result_path = profile_path(normalized_url)
                    if result_path != linkedin_path:
                        continue
                if "instagram.com" in url:
                    if not instagram_handle:
                        continue
                    instagram_path = urllib.parse.urlparse(normalized_url).path.strip("/").split("/")
                    if not instagram_path or instagram_path[0].lower() != instagram_handle.lower():
                        continue
                if normalized_url and normalized_url in seen_urls:
                    continue
                if normalized_url:
                    seen_urls.add(normalized_url)
                sources.append({
                    "title": title,
                    "url": normalized_url or url,
                    "content": content,
                })
        except Exception as exc:
            print(f"Ricerca presenza digitale non riuscita per '{query}': {exc}")

    return sources[:8]


def build_fallback_digital_analysis(user: Dict, sources: List[Dict[str, str]]) -> Dict:
    has_linkedin = bool(user.get("linkedin_url"))
    has_instagram = bool(user.get("instagram_handle"))
    has_cv_text = bool(user.get("cv_text"))
    score = 58 + (18 if has_linkedin else 0) + (8 if has_instagram else 0) + (6 if has_cv_text else 0)
    score = min(score, 86)

    return {
        "score": score,
        "headline": "Analisi preliminare completata",
        "summary": (
            "Ho salvato i profili inseriti e creato una prima valutazione di coerenza. "
            "Per un report piu accurato inserisci un link LinkedIn pubblico e profili aggiornati."
        ),
        "findings": [
            {
                "title": "Coerenza LinkedIn",
                "status": "success" if has_linkedin else "warning",
                "description": (
                    "LinkedIn e presente e puo essere confrontato con CV, ruolo target e percorso."
                    if has_linkedin
                    else "Manca un link LinkedIn: per un recruiter e spesso il primo punto di verifica."
                ),
                "coach_tip": (
                    "Allinea headline, esperienze, competenze e date con il CV prima di candidarti."
                ),
            },
            {
                "title": "Foto e contenuti pubblici",
                "status": "success" if has_instagram else "warning",
                "description": (
                    "Instagram e stato inserito come profilo da controllare: il focus e verificare foto, bio e contenuti pubblici rispetto al posizionamento professionale."
                    if has_instagram
                    else "Non hai inserito Instagram: se lo usi pubblicamente, controlla che foto, bio e contenuti siano coerenti con il profilo professionale."
                ),
                "coach_tip": "Mantieni foto profilo, bio e contenuti recenti coerenti con il ruolo per cui ti candidi.",
            },
        ],
        "sources": sources,
    }


def build_clean_digital_analysis(user: Dict, sources: List[Dict[str, str]], score: int) -> Dict:
    has_linkedin = bool(user.get("linkedin_url"))
    has_instagram = bool(user.get("instagram_handle"))

    findings = [
        {
            "title": "LinkedIn",
            "status": "success" if has_linkedin else "warning",
            "description": (
                "Il profilo LinkedIn inserito viene considerato come riferimento principale per headline, formazione, esperienze e competenze."
                if has_linkedin
                else "Non hai inserito un profilo LinkedIn: aggiungerlo rende piu forte la candidatura."
            ),
            "coach_tip": "Allinea headline, ruolo target, esperienze, date e competenze con il CV.",
        },
        {
            "title": "Coerenza CV/profili",
            "status": "success",
            "description": "L'analisi usa solo CV e profili che hai inserito tu, evitando confronti con omonimi o risultati non verificati.",
            "coach_tip": "Controlla che ruolo target, formazione e competenze principali dicano la stessa cosa su CV e LinkedIn.",
        },
        {
            "title": "Foto e contenuti pubblici",
            "status": "success" if has_instagram else "warning",
            "description": (
                "Instagram e stato collegato come profilo esatto: la verifica riguarda la coerenza di foto, bio e contenuti pubblici."
                if has_instagram
                else "Instagram non e stato collegato: se il profilo e pubblico, vale la pena controllarlo prima di candidarti."
            ),
            "coach_tip": "Evita contenuti pubblici che possano confondere il posizionamento professionale.",
        },
        {
            "title": "Impatto recruiter",
            "status": "success" if has_linkedin else "warning",
            "description": "Un recruiter vedra un percorso piu credibile se CV, LinkedIn e profili pubblici raccontano la stessa direzione professionale.",
            "coach_tip": "Usa le stesse parole chiave del ruolo target nei punti piu visibili del profilo.",
        },
    ]

    return {
        "score": score,
        "headline": "Presenza digitale da allineare con cura",
        "summary": "La valutazione considera solo i profili che hai inserito tu. Il punteggio misura quanto CV, LinkedIn e profili pubblici aiutano il tuo posizionamento professionale.",
        "findings": findings,
        "sources": sources,
    }


def analyze_digital_profile(user: Dict, sources: List[Dict[str, str]]) -> Dict:
    fallback = build_fallback_digital_analysis(user, sources)
    has_linkedin = bool(user.get("linkedin_url"))
    has_instagram = bool(user.get("instagram_handle"))
    minimum_score = 76 if has_linkedin and has_instagram else 68 if has_linkedin else 55
    prompt = f"""
Sei un consulente di personal branding e recruiting.

Valuta la coerenza professionale della presenza digitale del candidato usando solo:
- dati del profilo candidato;
- testo CV disponibile;
- link inseriti;
- estratti web pubblici forniti.

Non affermare di aver visto immagini se dagli estratti non emergono informazioni visive. Se il candidato ha inserito Instagram o profili con foto, valuta il rischio reputazionale come controllo consigliato sulle immagini pubblicate.

Profilo candidato:
- Nome: {user.get("name", "")}
- Email: {user.get("email", "")}
- Percorso di studi: {user.get("education", "")}
- Ruolo target: {user.get("target_role", "")}
- Settore: {user.get("sector", "")}
- Livello esperienza: {user.get("experience_level", "")}
- LinkedIn: {user.get("linkedin_url", "")}
- Portfolio/X: {user.get("portfolio_url", "")}
- Instagram: {user.get("instagram_handle", "")}

Estratto CV:
{(user.get("cv_text") or "")[:5000]}

Fonti pubbliche trovate:
{sources_to_prompt(sources)}

Restituisci SOLO JSON valido con questa struttura:
{{
  "score": 0,
  "headline": "titolo breve del risultato",
  "summary": "sintesi concreta per il candidato",
  "findings": [
    {{
      "title": "area analizzata",
      "status": "success oppure warning",
      "description": "cosa e stato trovato o non trovato",
      "coach_tip": "azione consigliata"
    }}
  ],
  "sources": []
}}

Regole:
- score intero 0-100.
- Non abbassare il punteggio solo perche il web restituisce poche fonti: se i link inseriti sono esatti, valuta la coerenza dei dati disponibili.
- Se LinkedIn e Instagram sono stati inseriti e non ci sono prove reali di incoerenza nelle fonti fornite, il punteggio non deve essere sotto 70.
- findings deve includere almeno LinkedIn, coerenza CV/profili, foto o contenuti pubblici, impatto recruiter.
- Valuta soprattutto headline LinkedIn, esperienze/date, competenze, formazione e coerenza con ruolo target.
- I profili social inseriti dal candidato sono autoritativi: non confrontare mai il candidato con profili LinkedIn, Instagram o portfolio non presenti nelle fonti.
- L'handle Instagram inserito dal candidato e autoritativo: non segnalare profili Instagram multipli o omonimi se non compaiono tra le fonti esatte.
- Se le fonti non contengono altri profili, non parlare di "diverse fonti", "profili multipli", omonimi o incongruenze con persone diverse.
- Non inventare dati non presenti.
- sources deve restare una lista vuota: le fonti reali vengono aggiunte dal backend.
"""

    try:
        result = extract_json(call_groq(prompt, temperature=0.25, max_tokens=1400))
        result["score"] = max(clamp_score(result.get("score", fallback["score"])), minimum_score)
        result["headline"] = result.get("headline") or fallback["headline"]
        result["summary"] = result.get("summary") or fallback["summary"]
        result["findings"] = result.get("findings") or fallback["findings"]
        result["sources"] = sources
        unsafe_text = json.dumps(result, ensure_ascii=False).lower()
        unsafe_patterns = [
            "profili multipli",
            "diverse fonti",
            "omonim",
            "silvia serra",
            "persona diversa",
            "nomi diversi",
        ]
        if any(pattern in unsafe_text for pattern in unsafe_patterns):
            return build_clean_digital_analysis(user, sources, result["score"])
        return result
    except Exception as exc:
        print(f"Analisi digitale AI non riuscita, uso fallback: {exc}")
        return fallback


def get_question_type_instructions(interview_type: str, role: str, company: str) -> str:
    """
    Restituisce istruzioni specifiche per generare domande diverse
    in base alla tipologia scelta dall'utente.
    """

    if interview_type == "conoscitive_motivazionali":
        return f"""
TIPOLOGIA: DOMANDE CONOSCITIVE E MOTIVAZIONALI

Obiettivo:
Capire chi è il candidato, cosa cerca, come ragiona, cosa si aspetta dall'azienda,
come si presenta e quanto è motivato per il ruolo e per {company}.

Le domande devono riguardare:
- presentazione personale;
- percorso di studi o esperienze;
- obiettivi professionali;
- aspettative rispetto all'azienda;
- motivazione per il ruolo;
- conoscenza dell'azienda;
- punti di forza e aree di miglioramento;
- hobby o interessi, se utili a capire la persona;
- lavoro di gruppo;
- gestione di difficoltà, conflitti o responsabilità;
- come il candidato si vede tra alcuni anni.

Le domande NON devono essere tecniche.
Le domande devono sembrare domande da recruiter HR.
"""

    if interview_type == "tecniche":
        return f"""
TIPOLOGIA: DOMANDE TECNICHE

Obiettivo:
Valutare le competenze tecniche del candidato rispetto al ruolo target: {role}.

Le domande devono essere specifiche per:
- ruolo selezionato;
- settore indicato dal candidato;
- strumenti, metodi, tecnologie o competenze richieste;
- progetti svolti;
- capacità di spiegare concetti tecnici;
- capacità di risolvere problemi operativi;
- capacità di applicare conoscenze teoriche a casi pratici.

Le domande NON devono essere generiche o motivazionali.
Devono servire a capire se il candidato sa ragionare tecnicamente.
"""

    if interview_type == "logica":
        return f"""
TIPOLOGIA: DOMANDE DI LOGICA, RAGIONAMENTO E PROBLEM SOLVING

Obiettivo:
Valutare il modo in cui il candidato ragiona, formula ipotesi, affronta problemi ambigui,
fa stime, riconosce trabocchetti e spiega il proprio processo mentale.

Le 10 domande devono alternare queste sottocategorie:

1. Domande di logica legate al ruolo o alle abilità della persona:
   - problemi di ragionamento applicati al ruolo {role};
   - casi in cui bisogna ordinare informazioni, prendere decisioni o analizzare vincoli;
   - situazioni realistiche ma mentalmente sfidanti.

2. Domande di stima/Fermi questions:
   - "Quanti Big Mac vengono venduti da McDonald’s ogni anno negli Stati Uniti?"
   - "Quante palline da ping pong servirebbero per riempire questa stanza?"
   - "Quante birre vengono consumate in media in un anno in Italia?"
   - domande simili, ma possibilmente adattate al settore o all'azienda {company}.

3. Domande a trabocchetto:
   - domande dove bisogna stare attenti alle assunzioni;
   - domande apparentemente semplici ma con un inganno logico;
   - domande che valutano attenzione e lucidità.

4. Serie numeriche o alfabetiche:
   - completare una sequenza di numeri;
   - completare una sequenza di lettere;
   - individuare la regola di una sequenza.

5. Mini business case/logica aziendale:
   - problemi di priorità, trade-off, risorse limitate;
   - decisioni con dati incompleti;
   - ragionamenti collegati almeno in parte all'azienda {company} o al ruolo {role}.

Regole specifiche:
- Le domande devono richiedere uno sforzo mentale, non una risposta motivazionale.
- Almeno 2 domande devono essere di stima.
- Almeno 2 domande devono essere a trabocchetto.
- Almeno 2 domande devono contenere una serie numerica o alfabetica.
- Almeno 2 domande devono essere collegate al ruolo {role} o all'azienda {company}.
- Ogni domanda deve chiedere al candidato di spiegare il ragionamento, non solo dare una risposta secca.
- Le domande devono essere realistiche per un colloquio.
"""

    return """
Genera domande di colloquio realistiche, coerenti con il profilo del candidato.
"""


def get_difficulty_instructions(difficulty: str) -> str:
    """
    Restituisce istruzioni specifiche in base al livello scelto.
    """

    if difficulty == "base":
        return """
LIVELLO: BASE

Le domande devono essere realistiche ma semplici.
Devono essere adatte a un candidato junior o a una persona alle prime esperienze.
Evita domande troppo tecniche, troppo lunghe o troppo astratte.
Le domande devono permettere al candidato di rispondere anche con esperienze universitarie, personali o di progetto.
Per la logica, usa problemi semplici, guidati e spiegabili.
"""

    if difficulty == "intermedio":
        return """
LIVELLO: INTERMEDIO

Le domande devono essere realistiche e leggermente sfidanti.
Devono richiedere esempi concreti, ragionamento e collegamento con il ruolo.
Le domande possono contenere casi pratici, situazioni lavorative o problemi da analizzare.
Per la logica, usa problemi di stima, ragionamento e piccoli trabocchetti di difficoltà media.
"""

    if difficulty == "avanzato":
        return """
LIVELLO: AVANZATO

Le domande devono essere più specifiche, complesse e selettive.
Devono simulare un colloquio più esigente.
Devono richiedere ragionamento strutturato, esempi solidi, capacità critica e conoscenza del ruolo.
Per le domande tecniche, usa casi più dettagliati e realistici.
Per le domande di logica, usa stime complesse, vincoli multipli, serie meno immediate, business case e problemi a trabocchetto.
"""

    return """
LIVELLO: INTERMEDIO

Le domande devono essere realistiche, coerenti con il ruolo e abbastanza sfidanti.
"""


def save_sources_for_question(cursor, question_id: int, sources: List[Dict[str, str]]):
    for source in sources:
        title = source.get("title", "").strip()
        url = source.get("url", "").strip()
        content = source.get("content", "").strip()

        if not url:
            continue

        cursor.execute("""
        INSERT OR IGNORE INTO web_sources (
            title,
            url,
            content
        )
        VALUES (?, ?, ?)
        """, (
            title,
            url,
            content
        ))

        cursor.execute("""
        SELECT id
        FROM web_sources
        WHERE url = ?
        """, (url,))

        row = cursor.fetchone()

        if not row:
            continue

        source_id = row[0]

        cursor.execute("""
        SELECT id
        FROM question_web_sources
        WHERE question_id = ? AND source_id = ?
        """, (
            question_id,
            source_id
        ))

        already_linked = cursor.fetchone()

        if already_linked:
            continue

        cursor.execute("""
        INSERT INTO question_web_sources (
            question_id,
            source_id
        )
        VALUES (?, ?)
        """, (
            question_id,
            source_id
        ))


# =========================
# ENDPOINT BASE / DEBUG
# =========================

@app.get("/")
def home():
    return {
        "message": "CareerCoach backend attivo con GroqCloud + Tavily Web Search",
        "groq_model": GROQ_MODEL
    }


@app.get("/debug")
def debug():
    return {
        "status": "ok",
        "message": "Backend FastAPI attivo",
        "groq_model": GROQ_MODEL,
        "has_groq_key": bool(GROQ_API_KEY),
        "has_tavily_key": bool(TAVILY_API_KEY)
    }


# =========================
# ENDPOINT UTENTI
# =========================

@app.post("/auth/register")
def register(data: RegisterRequest):
    email = validate_email_address(data.email)
    phone = validate_phone(data.phone)
    validate_password(data.password)

    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Inserisci il nome.")

    verification_token = make_token()
    expires_at = utc_now() + timedelta(hours=24)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE lower(email) = lower(?)", (email,))
    existing_email = cursor.fetchone()
    if existing_email:
        conn.close()
        raise HTTPException(status_code=409, detail="Esiste già un account con questa email.")

    if phone:
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        existing_phone = cursor.fetchone()
        if existing_phone:
            conn.close()
            raise HTTPException(status_code=409, detail="Questo numero è già associato a un account.")

    cursor.execute("""
    INSERT INTO users (
        name,
        email,
        phone,
        password_hash,
        email_verified,
        email_verification_token,
        email_verification_expires_at,
        education,
        target_role,
        sector,
        experience_level,
        interview_language
    )
    VALUES (?, ?, ?, ?, 0, ?, ?, '', '', '', 'Junior', 'Italiano')
    """, (
        name,
        email,
        phone,
        hash_password(data.password),
        verification_token,
        expires_at.isoformat(),
    ))

    conn.commit()
    conn.close()

    verification_link = make_frontend_link("verify", verification_token)
    email_sent = send_email(
        email,
        "Verifica il tuo account CareerCoach",
        (
            "Ciao,\n\n"
            "per attivare il tuo account CareerCoach apri questo link:\n"
            f"{verification_link}\n\n"
            "Il link scade tra 24 ore."
        ),
    )

    return {
        "message": "Account creato. Controlla la tua email per verificare l'accesso.",
        "email_sent": email_sent,
        "preview_link": None if email_sent else verification_link,
    }


@app.post("/auth/verify-email")
def verify_email(data: TokenRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, email_verification_expires_at
    FROM users
    WHERE email_verification_token = ?
    """, (data.token,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=400, detail="Link di verifica non valido.")

    user_id, expires_at = row
    if expires_at and datetime.fromisoformat(expires_at) < utc_now():
        conn.close()
        raise HTTPException(status_code=400, detail="Link di verifica scaduto. Registrati di nuovo o richiedi un nuovo link.")

    cursor.execute("""
    UPDATE users
    SET email_verified = 1,
        email_verification_token = NULL,
        email_verification_expires_at = NULL
    WHERE id = ?
    """, (user_id,))

    session_token = create_session(cursor, user_id)
    user = fetch_user_by_id(cursor, user_id)
    conn.commit()
    conn.close()

    return {
        "token": session_token,
        "user": user_to_response(user),
        "message": "Email verificata correttamente.",
    }


@app.post("/auth/login")
def login(data: LoginRequest):
    identifier = data.identifier.strip()
    password = data.password

    conn = get_connection()
    cursor = conn.cursor()

    if "@" in identifier:
        identifier = validate_email_address(identifier)
        cursor.execute("""
        SELECT id, password_hash, email_verified
        FROM users
        WHERE lower(email) = lower(?)
        """, (identifier,))
    else:
        phone = validate_phone(identifier)
        cursor.execute("""
        SELECT id, password_hash, email_verified
        FROM users
        WHERE phone = ?
        """, (phone,))

    row = cursor.fetchone()
    if not row or not verify_password(password, row[1]):
        conn.close()
        raise HTTPException(status_code=401, detail="Email/telefono o password non corretti.")

    if not row[2]:
        conn.close()
        raise HTTPException(status_code=403, detail="Verifica prima la tua email tramite il link ricevuto.")

    session_token = create_session(cursor, row[0])
    user = fetch_user_by_id(cursor, row[0])
    conn.commit()
    conn.close()

    return {
        "token": session_token,
        "user": user_to_response(user),
    }


@app.get("/auth/me")
def get_current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sessione mancante.")

    token = authorization.replace("Bearer ", "", 1).strip()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_id, expires_at
    FROM user_sessions
    WHERE token = ?
    """, (token,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Sessione non valida.")

    if datetime.fromisoformat(session[1]) < utc_now():
        cursor.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=401, detail="Sessione scaduta.")

    user = fetch_user_by_id(cursor, session[0])
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato.")

    return {"user": user_to_response(user)}


@app.post("/auth/logout")
def logout(data: TokenRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_sessions WHERE token = ?", (data.token,))
    conn.commit()
    conn.close()
    return {"message": "Logout effettuato."}


@app.get("/auth/oauth/redirect-uris")
def oauth_redirect_uris():
    return {
        "google": make_oauth_callback_url("google"),
        "apple": make_oauth_callback_url("apple"),
        "linkedin": make_oauth_callback_url("linkedin"),
    }


@app.get("/auth/oauth/status")
def oauth_status():
    providers = ["google", "apple", "linkedin"]
    status = {}

    for provider in providers:
        client_id = {
            "google": GOOGLE_CLIENT_ID,
            "apple": APPLE_CLIENT_ID,
            "linkedin": LINKEDIN_CLIENT_ID,
        }.get(provider)
        client_secret = {
            "google": GOOGLE_CLIENT_SECRET,
            "apple": APPLE_CLIENT_SECRET,
            "linkedin": LINKEDIN_CLIENT_SECRET,
        }.get(provider)

        try:
            config = get_oauth_config(provider)
            scope = config["scope"]
            configured = True
        except HTTPException:
            scope = None
            configured = False

        status[provider] = {
            "configured": configured,
            "has_client_id": bool(client_id),
            "has_client_secret": bool(client_secret),
            "redirect_uri": make_oauth_callback_url(provider),
            "scope": scope,
        }

    return status


@app.get("/auth/oauth/{provider}/start")
def start_oauth(provider: str):
    provider = normalize_oauth_provider(provider)
    conn = get_connection()
    cursor = conn.cursor()
    state = create_oauth_state(cursor, provider)
    conn.commit()
    conn.close()

    return RedirectResponse(build_oauth_authorization_url(provider, state))


@app.get("/auth/oauth/{provider}/url")
def get_oauth_url(provider: str):
    provider = normalize_oauth_provider(provider)
    conn = get_connection()
    cursor = conn.cursor()
    state = create_oauth_state(cursor, provider)
    auth_url = build_oauth_authorization_url(provider, state)
    conn.commit()
    conn.close()

    return {"auth_url": auth_url}


@app.get("/auth/oauth/{provider}/callback")
def oauth_callback(provider: str, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    provider = normalize_oauth_provider(provider)

    if error:
        raise HTTPException(status_code=400, detail=f"Accesso social annullato: {error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Risposta OAuth incompleta.")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        consume_oauth_state(cursor, provider, state)
        profile = fetch_oauth_profile(provider, code)
        user_id = find_or_create_oauth_user(cursor, provider, profile)
        session_token = create_session(cursor, user_id)
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(make_frontend_oauth_link(session_token))


@app.get("/auth/linkedin/callback")
def linkedin_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    return oauth_callback("linkedin", code=code, state=state, error=error)


@app.post("/auth/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    identifier = data.identifier.strip()
    conn = get_connection()
    cursor = conn.cursor()

    if "@" in identifier:
        identifier = validate_email_address(identifier)
        cursor.execute("SELECT id, email FROM users WHERE lower(email) = lower(?)", (identifier,))
    else:
        phone = validate_phone(identifier)
        cursor.execute("SELECT id, email FROM users WHERE phone = ?", (phone,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"message": "Se l'account esiste, riceverai un link per reimpostare la password."}

    token = make_token()
    expires_at = utc_now() + timedelta(hours=1)
    cursor.execute("""
    UPDATE users
    SET password_reset_token = ?,
        password_reset_expires_at = ?
    WHERE id = ?
    """, (token, expires_at.isoformat(), row[0]))
    conn.commit()
    conn.close()

    reset_link = make_frontend_link("reset", token)
    email_sent = send_email(
        row[1],
        "Recupero password CareerCoach",
        (
            "Ciao,\n\n"
            "per scegliere una nuova password apri questo link:\n"
            f"{reset_link}\n\n"
            "Il link scade tra 1 ora."
        ),
    )

    return {
        "message": "Se l'account esiste, riceverai un link per reimpostare la password.",
        "email_sent": email_sent,
        "preview_link": None if email_sent else reset_link,
    }


@app.post("/auth/reset-password")
def reset_password(data: ResetPasswordRequest):
    validate_password(data.password)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, password_reset_expires_at
    FROM users
    WHERE password_reset_token = ?
    """, (data.token,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=400, detail="Link di recupero non valido.")

    if row[1] and datetime.fromisoformat(row[1]) < utc_now():
        conn.close()
        raise HTTPException(status_code=400, detail="Link di recupero scaduto.")

    cursor.execute("""
    UPDATE users
    SET password_hash = ?,
        password_reset_token = NULL,
        password_reset_expires_at = NULL
    WHERE id = ?
    """, (hash_password(data.password), row[0]))
    cursor.execute("DELETE FROM user_sessions WHERE user_id = ?", (row[0],))
    conn.commit()
    conn.close()

    return {"message": "Password aggiornata. Ora puoi accedere."}


@app.post("/users")
def create_user(data: UserCreate):
    email = validate_email_address(data.email) if data.email else None
    phone = validate_phone(data.phone)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (
        name,
        email,
        phone,
        education,
        target_role,
        sector,
        experience_level,
        interview_language
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.name,
        email,
        phone,
        data.education,
        data.target_role,
        data.sector,
        data.experience_level,
        data.interview_language
    ))

    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return {
        "user_id": user_id,
        "message": "Profilo creato correttamente"
    }


@app.get("/users/{user_id}")
def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        id,
        name,
        email,
        education,
        target_role,
        sector,
        experience_level,
        interview_language,
        phone,
        email_verified,
        cv_filename,
        cv_content_type,
        cv_size,
        cv_text,
        cv_uploaded_at,
        linkedin_url,
        portfolio_url,
        instagram_handle,
        auth_provider
    FROM users
    WHERE id = ?
    """, (user_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "education": row[3],
        "target_role": row[4],
        "sector": row[5],
        "experience_level": row[6],
        "interview_language": row[7],
        "phone": row[8],
        "email_verified": bool(row[9]),
        "cv_filename": row[10],
        "cv_uploaded": bool(row[10]),
        "cv_uploaded_at": row[14],
        "linkedin_url": row[15],
        "portfolio_url": row[16],
        "instagram_handle": row[17],
        "auth_provider": row[18],
    }


@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Utente non trovato.")

    cursor.execute("""
    DELETE FROM question_web_sources
    WHERE question_id IN (
        SELECT q.id
        FROM questions q
        JOIN interview_sessions s ON q.session_id = s.id
        WHERE s.user_id = ?
    )
    """, (user_id,))

    cursor.execute("""
    DELETE FROM answers
    WHERE question_id IN (
        SELECT q.id
        FROM questions q
        JOIN interview_sessions s ON q.session_id = s.id
        WHERE s.user_id = ?
    )
    """, (user_id,))

    cursor.execute("""
    DELETE FROM questions
    WHERE session_id IN (
        SELECT id
        FROM interview_sessions
        WHERE user_id = ?
    )
    """, (user_id,))

    cursor.execute("DELETE FROM interview_sessions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

    conn.commit()
    conn.close()

    return {"message": "Profilo eliminato correttamente."}


@app.put("/users/{user_id}")
def update_user(user_id: int, data: UserUpdate):
    email = validate_email_address(data.email) if data.email else None
    phone = validate_phone(data.phone)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))
    existing_user = cursor.fetchone()
    if not existing_user:
        conn.close()
        raise HTTPException(status_code=404, detail="Utente non trovato.")

    if email:
        cursor.execute("SELECT id FROM users WHERE lower(email) = lower(?) AND id != ?", (email, user_id))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=409, detail="Email già associata a un altro account.")

    if phone:
        cursor.execute("SELECT id FROM users WHERE phone = ? AND id != ?", (phone, user_id))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=409, detail="Numero già associato a un altro account.")

    email_changed = email and existing_user[1] and email.lower() != existing_user[1].lower()
    verification_token = make_token() if email_changed else None
    verification_expires = (utc_now() + timedelta(hours=24)).isoformat() if email_changed else None

    cursor.execute("""
    UPDATE users
    SET name = ?,
        email = ?,
        phone = ?,
        education = ?,
        target_role = ?,
        sector = ?,
        experience_level = ?,
        interview_language = ?,
        email_verified = CASE WHEN ? THEN 0 ELSE email_verified END,
        email_verification_token = CASE WHEN ? THEN ? ELSE email_verification_token END,
        email_verification_expires_at = CASE WHEN ? THEN ? ELSE email_verification_expires_at END
    WHERE id = ?
    """, (
        data.name,
        email,
        phone,
        data.education,
        data.target_role,
        data.sector,
        data.experience_level,
        data.interview_language,
        1 if email_changed else 0,
        1 if email_changed else 0,
        verification_token,
        1 if email_changed else 0,
        verification_expires,
        user_id,
    ))

    conn.commit()
    user = fetch_user_by_id(cursor, user_id)
    conn.close()

    preview_link = None
    email_sent = False
    if email_changed:
        preview_link = make_frontend_link("verify", verification_token)
        email_sent = send_email(
            email,
            "Verifica il nuovo indirizzo email CareerCoach",
            (
                "Ciao,\n\n"
                "per confermare il nuovo indirizzo email apri questo link:\n"
                f"{preview_link}\n\n"
                "Il link scade tra 24 ore."
            ),
        )

    return {
        "user": user_to_response(user),
        "message": "Profilo aggiornato correttamente.",
        "email_sent": email_sent,
        "preview_link": None if email_sent else preview_link,
    }


@app.delete("/users/{user_id}/cv")
def delete_user_cv(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Utente non trovato.")

    cursor.execute("""
    UPDATE users
    SET cv_filename = NULL,
        cv_content_type = NULL,
        cv_size = NULL,
        cv_text = NULL,
        cv_file_base64 = NULL,
        cv_uploaded_at = NULL,
        digital_analysis_json = NULL
    WHERE id = ?
    """, (user_id,))

    conn.commit()
    user = fetch_user_by_id(cursor, user_id)
    conn.close()

    return {
        "user": user_to_response(user),
        "message": "CV eliminato correttamente.",
    }


@app.post("/validate-cv-file")
async def validate_cv_file(file: UploadFile = File(...)):
    filename = (file.filename or "").strip()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_extensions = {"pdf", "docx", "txt"}

    if not filename or extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Carica un file PDF, DOCX o TXT.")

    file_bytes = await file.read()

    print("=== VALIDAZIONE CV ===")
    print("Filename:", file.filename)
    print("Content type:", file.content_type)
    print("File size:", len(file_bytes))

    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Il CV non puo superare 5MB.")

    debug = {
        "filename": filename,
        "content_type": file.content_type,
        "file_size": len(file_bytes),
        "extension": extension,
        "text_length": 0,
        "extraction_method": "",
    }

    if not file_bytes:
        return {
            "is_cv": False,
            "confidence": 0,
            "reason": "Il file e vuoto.",
            "detected_sections": [],
            "debug": debug,
        }

    extracted_text, extraction_method = extract_text_from_file_bytes(file_bytes, filename)
    normalized_text = clean_extracted_text(extracted_text)
    debug["text_length"] = len(normalized_text)
    debug["extraction_method"] = extraction_method

    print("Extraction method:", extraction_method)
    print("Text length:", len(normalized_text))
    print("Text preview:", normalized_text[:1000])

    if len(normalized_text) == 0:
        return {
            "is_cv": False,
            "confidence": 0,
            "reason": "Non riesco a estrarre testo dal file. Potrebbe essere un PDF scannerizzato o composto da immagini.",
            "detected_sections": [],
            "debug": debug,
        }

    heuristic = analyze_cv_heuristics(normalized_text)
    heuristic_score = heuristic["score"]

    if len(normalized_text) < 50 and heuristic_score < 35:
        return {
            "is_cv": False,
            "confidence": heuristic_score,
            "reason": "Il testo estratto e molto breve e non contiene abbastanza elementi tipici di un curriculum.",
            "detected_sections": heuristic["detected_sections"],
            "debug": debug,
        }

    strong_cv_sections = {"contatti", "formazione", "esperienze professionali", "competenze", "lingue"}
    strong_section_count = len(strong_cv_sections.intersection(set(heuristic["detected_sections"])))

    if heuristic_score >= 45:
        is_cv = True
        confidence = heuristic_score
        reason = heuristic["reason"]
    elif heuristic_score >= 35 and strong_section_count >= 2:
        is_cv = True
        confidence = heuristic_score
        reason = heuristic["reason"]
    else:
        is_cv = False
        confidence = heuristic_score
        reason = "Il documento e leggibile, ma non contiene abbastanza elementi tipici di un curriculum."

    return {
        "is_cv": is_cv,
        "confidence": clamp_score(confidence),
        "reason": reason,
        "detected_sections": heuristic["detected_sections"],
        "debug": debug,
    }


@app.post("/users/{user_id}/cv")
def upload_user_cv(user_id: int, data: UserCvUpload):
    filename = data.filename.strip()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_extensions = {"pdf", "docx", "txt"}

    if not filename or extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Carica un file PDF, DOCX o TXT.")

    if data.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Il CV non puo superare 5MB.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Utente non trovato.")

    cursor.execute("""
    UPDATE users
    SET cv_filename = ?,
        cv_content_type = ?,
        cv_size = ?,
        cv_text = ?,
        cv_file_base64 = ?,
        cv_uploaded_at = CURRENT_TIMESTAMP,
        education = CASE WHEN education IS NULL OR trim(education) = '' THEN 'Da CV caricato' ELSE education END,
        target_role = CASE WHEN target_role IS NULL OR trim(target_role) = '' THEN 'Da definire' ELSE target_role END,
        sector = CASE WHEN sector IS NULL OR trim(sector) = '' THEN 'Da definire' ELSE sector END,
        experience_level = CASE WHEN experience_level IS NULL OR trim(experience_level) = '' THEN 'Junior' ELSE experience_level END,
        interview_language = CASE WHEN interview_language IS NULL OR trim(interview_language) = '' THEN 'Italiano' ELSE interview_language END
    WHERE id = ?
    """, (
        filename,
        data.content_type,
        data.size,
        (data.text or "")[:20000],
        data.file_base64 or "",
        user_id,
    ))

    conn.commit()
    user = fetch_user_by_id(cursor, user_id)
    conn.close()

    return {
        "user": user_to_response(user),
        "message": "CV salvato nel profilo.",
    }


@app.get("/users/{user_id}/cv-file")
def get_user_cv_file(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    user = fetch_user_by_id(cursor, user_id)
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato.")

    if not user[10] or not user[14]:
        raise HTTPException(status_code=404, detail="CV non trovato.")

    return {
        "filename": user[10],
        "content_type": user[11] or "application/octet-stream",
        "size": user[12],
        "text": user[13] or "",
        "file_base64": user[14],
        "uploaded_at": user[15],
    }


@app.put("/users/{user_id}/digital-presence")
def update_digital_presence(user_id: int, data: DigitalPresenceUpdate):
    conn = get_connection()
    cursor = conn.cursor()
    existing_user = fetch_user_by_id(cursor, user_id)
    if not existing_user:
        conn.close()
        raise HTTPException(status_code=404, detail="Utente non trovato.")

    public_user = user_to_response(existing_user)
    public_user["cv_text"] = existing_user[13] or ""
    public_user["linkedin_url"] = (data.linkedin_url or "").strip()
    public_user["portfolio_url"] = (data.portfolio_url or "").strip()
    instagram_handle = normalize_instagram_handle(data.instagram_handle)
    public_user["instagram_handle"] = f"@{instagram_handle}" if instagram_handle else ""

    sources = search_public_profile_signals(public_user, data)
    digital_analysis = analyze_digital_profile(public_user, sources)
    digital_analysis_json = json.dumps(digital_analysis, ensure_ascii=False)

    cursor.execute("""
    UPDATE users
    SET linkedin_url = ?,
        portfolio_url = ?,
        instagram_handle = ?,
        digital_analysis_json = ?
    WHERE id = ?
    """, (
        public_user["linkedin_url"],
        public_user["portfolio_url"],
        public_user["instagram_handle"],
        digital_analysis_json,
        user_id,
    ))

    conn.commit()
    user = fetch_user_by_id(cursor, user_id)
    conn.close()

    return {
        "user": user_to_response(user),
        "analysis": digital_analysis,
        "message": "Presenza digitale salvata.",
    }


# =========================
# ENDPOINT RICERCA WEB
# =========================

@app.post("/search-interview-questions")
def search_interview_questions(data: SearchInterviewQuestionsRequest):
    sources = search_web_interview_questions(
        company=data.company,
        role=data.role,
        interview_type=data.interview_type,
        language=data.language
    )

    return {
        "query": build_search_query(
            data.company,
            data.role,
            data.interview_type,
            data.language
        ),
        "sources": sources
    }


# =========================
# ENDPOINT GENERA 10 DOMANDE
# =========================

@app.post("/generate-question")
def generate_question(data: GenerateQuestionRequest):
    print("Endpoint /generate-question chiamato.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        id,
        name,
        education,
        target_role,
        sector,
        experience_level,
        interview_language
    FROM users
    WHERE id = ?
    """, (data.user_id,))

    user = cursor.fetchone()

    if not user:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Utente non trovato. Prima devi creare il profilo con POST /users."
        )

    user_id, name, education, target_role, sector, experience_level, interview_language = user

    company = data.company or "Generica"
    question_mode = data.question_mode or "web"

    sources = []

    if question_mode in ["web", "mixed"]:
        sources = search_web_interview_questions(
            company=company,
            role=target_role,
            interview_type=data.interview_type,
            language=interview_language
        )

    if not sources and question_mode in ["web", "mixed"]:
        print("Nessuna fonte web trovata. Procedo con generazione AI basata sul profilo.")

    sources_text = sources_to_prompt(sources)

    question_type_instructions = get_question_type_instructions(
        interview_type=data.interview_type,
        role=target_role,
        company=company
    )

    difficulty_instructions = get_difficulty_instructions(data.difficulty)

    if question_mode == "ai":
        prompt = f"""
Sei un recruiter esperto.

Devi generare 10 domande di colloquio per questo candidato.

Profilo candidato:
- Nome: {name}
- Percorso di studi: {education}
- Ruolo target: {target_role}
- Settore: {sector}
- Livello esperienza: {experience_level}
- Lingua colloquio: {interview_language}
- Azienda target: {company}
- Tipo colloquio: {data.interview_type}
- Difficoltà: {data.difficulty}

Istruzioni sulla tipologia scelta:
{question_type_instructions}

Istruzioni sul livello di difficoltà:
{difficulty_instructions}

Le 10 domande devono simulare un colloquio realistico.
Devono essere diverse tra loro e progressive.
Devono rispettare rigorosamente la tipologia scelta: {data.interview_type}.

Regole:
- Non aggiungere testo prima o dopo il JSON.
- Non scrivere frasi introduttive come "Ecco le 10 domande".
- Scrivi esattamente 10 domande.
- Ogni elemento della lista deve essere una domanda vera e deve finire con il punto interrogativo.
- Le domande devono essere coerenti con ruolo, azienda, livello e difficoltà.
- Non numerare le domande dentro il testo.

Restituisci SOLO un JSON valido.
La struttura deve essere ESATTAMENTE questa:

{{
  "questions": [
    "Prima domanda?",
    "Seconda domanda?",
    "Terza domanda?",
    "Quarta domanda?",
    "Quinta domanda?",
    "Sesta domanda?",
    "Settima domanda?",
    "Ottava domanda?",
    "Nona domanda?",
    "Decima domanda?"
  ]
}}
"""
    else:
        prompt = f"""
Sei un recruiter esperto.

Devi generare 10 domande di colloquio realistiche per un candidato, ispirandoti ai risultati web trovati.

Profilo candidato:
- Nome: {name}
- Percorso di studi: {education}
- Ruolo target: {target_role}
- Settore: {sector}
- Livello esperienza: {experience_level}
- Lingua colloquio: {interview_language}
- Azienda target: {company}
- Tipo colloquio: {data.interview_type}
- Difficoltà: {data.difficulty}

Risultati web trovati:
{sources_text}

Istruzioni sulla tipologia scelta:
{question_type_instructions}

Istruzioni sul livello di difficoltà:
{difficulty_instructions}

Le 10 domande devono simulare un colloquio realistico.
Devono essere diverse tra loro e progressive.
Devono rispettare rigorosamente la tipologia scelta: {data.interview_type}.

Regole:
- Non copiare frasi lunghe dalle fonti.
- Non dire "secondo la fonte".
- Genera domande originali ma coerenti con i temi ricorrenti nei risultati.
- Se i risultati sono poco pertinenti, usa comunque il profilo candidato e il ruolo target.
- Non aggiungere testo prima o dopo il JSON.
- Non scrivere frasi introduttive come "Ecco le 10 domande".
- Scrivi esattamente 10 domande.
- Ogni elemento della lista deve essere una domanda vera e deve finire con il punto interrogativo.
- Le domande devono essere coerenti con ruolo, azienda, livello e difficoltà.
- Non numerare le domande dentro il testo.

Restituisci SOLO un JSON valido.
La struttura deve essere ESATTAMENTE questa:

{{
  "questions": [
    "Prima domanda?",
    "Seconda domanda?",
    "Terza domanda?",
    "Quarta domanda?",
    "Quinta domanda?",
    "Sesta domanda?",
    "Settima domanda?",
    "Ottava domanda?",
    "Nona domanda?",
    "Decima domanda?"
  ]
}}
"""

    try:
        raw_questions = call_groq(prompt, temperature=0.3, max_tokens=1400)

        print("OUTPUT GREZZO GROQ DOMANDE:")
        print(raw_questions)

        questions_list = extract_questions_list(raw_questions)

        print("DOMANDE ESTRATTE:")
        print(questions_list)

    except Exception as e:
        conn.close()
        raise e

    if data.interview_type == "conoscitive_motivazionali":
        fallback_questions = [
            "Parlami di te e del tuo percorso.",
            "Perché ti interessa questa posizione?",
            "Cosa sai della nostra azienda?",
            "Quali sono i tuoi obiettivi professionali?",
            "Come ti vedi tra cinque anni?",
            "Quali sono i tuoi punti di forza?",
            "Qual è un aspetto su cui vorresti migliorare?",
            "Raccontami una situazione in cui hai lavorato in gruppo.",
            "Cosa ti aspetti da questa esperienza lavorativa?",
            "Perché pensi di essere adatto a questo ruolo?"
        ]

    elif data.interview_type == "tecniche":
        fallback_questions = [
            f"Quali competenze tecniche ritieni fondamentali per il ruolo di {target_role}?",
            "Raccontami un progetto tecnico che hai svolto e quali problemi hai incontrato.",
            "Come affronteresti un problema tecnico che non sai risolvere subito?",
            "Quali strumenti o tecnologie conosci che potrebbero essere utili per questo ruolo?",
            "Come verificheresti la correttezza del tuo lavoro tecnico?",
            "Descrivi un caso in cui hai dovuto analizzare dati, codice, requisiti o informazioni tecniche.",
            "Come spiegheresti un concetto tecnico complesso a una persona non tecnica?",
            "Qual è una competenza tecnica che vuoi migliorare?",
            "Come ti organizzi quando devi completare un task tecnico entro una scadenza?",
            "Quale esperienza ti ha aiutato di più a sviluppare competenze utili per questo ruolo?"
        ]

    elif data.interview_type == "logica":
        fallback_questions = [
            f"Immagina di lavorare come {target_role}: hai tre attività urgenti, risorse limitate e informazioni incomplete. Come decideresti da cosa partire e perché?",
            "Quante palline da ping pong servirebbero, secondo te, per riempire la stanza in cui ti trovi? Spiega il ragionamento.",
            "Completa la serie numerica e spiega la regola: 2, 6, 12, 20, 30, ?",
            "Qual è l’angolo tra la lancetta dell’ora e quella dei minuti alle tre e quindici? Spiega il procedimento.",
            f"Se {company} dovesse stimare quanti utenti usano un suo servizio in un giorno, quali ipotesi faresti?",
            "Completa la serie di lettere e spiega la logica: A, C, F, J, O, ?",
            "Quanti Big Mac vengono venduti da McDonald’s ogni anno negli Stati Uniti? Non serve il numero esatto: spiega come lo stimeresti.",
            "Una procedura funziona nel 90% dei casi, ma fallisce nel restante 10%. Come analizzeresti il problema?",
            "Se un cliente ti fornisse dati contraddittori, come ragioneresti per capire quale informazione è più affidabile?",
            "Quante birre vengono consumate in media in un anno in Italia? Spiega quali dati useresti per stimarlo."
        ]

    else:
        fallback_questions = [
            "Parlami brevemente di te e del tuo percorso.",
            "Perché ti interessa questa posizione?",
            "Quali competenze pensi di poter portare in questo ruolo?",
            "Raccontami un progetto o un’esperienza rilevante per questa posizione.",
            "Qual è stata una difficoltà che hai affrontato e come l’hai gestita?",
            "Come ti organizzi quando hai una scadenza importante?",
            "Descrivi una situazione in cui hai lavorato in team.",
            "Qual è un tuo punto di forza e come lo useresti in questo ruolo?",
            "Qual è un aspetto su cui vuoi migliorare professionalmente?",
            "Hai qualche domanda sull’azienda o sul ruolo?"
        ]

    while len(questions_list) < 10:
        questions_list.append(fallback_questions[len(questions_list)])

    questions_list = questions_list[:10]

    sources_json = json.dumps(sources, ensure_ascii=False)

    cursor.execute("""
    INSERT INTO interview_sessions (
        user_id,
        interview_type,
        difficulty,
        company,
        question_mode
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        data.interview_type,
        data.difficulty,
        company,
        question_mode
    ))

    session_id = cursor.lastrowid

    saved_questions = []

    for question_text in questions_list:
        cursor.execute("""
        INSERT INTO questions (
            session_id,
            question_text,
            category,
            difficulty,
            company,
            question_mode,
            sources_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            question_text,
            data.interview_type,
            data.difficulty,
            company,
            question_mode,
            sources_json
        ))

        question_id = cursor.lastrowid

        save_sources_for_question(cursor, question_id, sources)

        saved_questions.append({
            "question_id": question_id,
            "question": question_text
        })

    conn.commit()
    conn.close()

    print("10 domande salvate e restituite al frontend.")

    return {
        "session_id": session_id,
        "questions": saved_questions,
        "question_id": saved_questions[0]["question_id"],
        "question": saved_questions[0]["question"],
        "company": company,
        "question_mode": question_mode
    }


# =========================
# ENDPOINT VALUTA RISPOSTA
# =========================

@app.post("/evaluate-answer")
def evaluate_answer(data: EvaluateAnswerRequest):
    print("Endpoint /evaluate-answer chiamato.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        q.id,
        q.question_text,
        q.session_id,
        q.company,
        q.question_mode,
        q.sources_json,
        s.user_id,
        s.interview_type,
        s.difficulty,
        u.name,
        u.education,
        u.target_role,
        u.sector,
        u.experience_level,
        u.interview_language
    FROM questions q
    JOIN interview_sessions s ON q.session_id = s.id
    JOIN users u ON s.user_id = u.id
    WHERE q.id = ?
    """, (data.question_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Domanda non trovata")

    (
        question_id,
        question_text,
        session_id,
        company,
        question_mode,
        sources_json,
        user_id,
        interview_type,
        difficulty,
        name,
        education,
        target_role,
        sector,
        experience_level,
        interview_language
    ) = row

    speech_metrics_json = get_speech_metrics_json(data.speech_metrics)

    zero_reason = get_zero_answer_reason(data.answer, question_text)

    if zero_reason:
        zero_result = build_zero_feedback(
            reason=zero_reason,
            question=question_text,
            interview_type=interview_type
        )

        save_answer_result(
            cursor=cursor,
            question_id=question_id,
            user_answer=data.answer,
            result=zero_result,
            speech_metrics_json=speech_metrics_json
        )

        cursor.execute("""
        UPDATE interview_sessions
        SET total_score = ?
        WHERE id = ?
        """, (
            zero_result["total_score"],
            session_id
        ))

        conn.commit()
        conn.close()

        return zero_result

    has_speech_metrics = data.speech_metrics is not None

    speech_info = ""

    if has_speech_metrics:
        speech_info = f"""
Dati sul parlato rilevati dal frontend:
- Durata risposta: {data.speech_metrics.duration_seconds} secondi
- Numero parole: {data.speech_metrics.words_count}
- Parole al minuto: {data.speech_metrics.words_per_minute}
- Numero parole riempitive: {data.speech_metrics.filler_words_count}
- Parole riempitive rilevate: {data.speech_metrics.filler_words}

Valuta anche il modo di parlare considerando:
- ritmo;
- chiarezza espositiva;
- parole riempitive;
- sicurezza percepita;
- sintesi;
- capacità di organizzare il discorso.
"""

    prompt = f"""
Sei un coach esperto di colloqui di lavoro.

Devi valutare la risposta di un candidato.

Profilo candidato:
- Nome: {name}
- Percorso di studi: {education}
- Ruolo target: {target_role}
- Settore: {sector}
- Livello esperienza: {experience_level}
- Lingua colloquio: {interview_language}
- Azienda target: {company}
- Tipo colloquio: {interview_type}
- Difficoltà: {difficulty}

Domanda del colloquio:
{question_text}

Risposta del candidato:
{data.answer}

{speech_info}

ISTRUZIONE PRIORITARIA:
Prima di assegnare qualsiasi punteggio, devi decidere internamente se la risposta è una vera risposta alla domanda oppure no.

La classificazione interna può essere solo:
- VALID_ANSWER
- NON_ANSWER

NON devi inserire questa classificazione nel JSON finale.

Una risposta è VALID_ANSWER solo se il candidato prova concretamente a rispondere alla domanda del colloquio.

Una risposta è NON_ANSWER se il candidato non fornisce un vero tentativo di risposta alla domanda posta.

Classifica sempre come NON_ANSWER qualsiasi risposta che:
- faccia una domanda invece di rispondere;
- chieda come viene valutata la risposta;
- chieda quali criteri vengono usati per valutare;
- chieda un voto, un punteggio, un giudizio o una correzione;
- chieda la risposta corretta;
- chieda aiuto, suggerimenti o indicazioni su cosa dire;
- parli del sistema di valutazione, del codice, della logica del progetto o dell'AI invece di rispondere;
- sia una frase di rinuncia, dubbio o incertezza;
- sia evasiva, fuori tema o non pertinente;
- sia troppo generica e non collegata alla domanda originale;
- sia una richiesta rivolta al recruiter, all'intervistatore o all'assistente;
- non dimostri alcuna competenza, esperienza, ragionamento o contenuto utile rispetto alla domanda.

Sono NON_ANSWER anche frasi grammaticalmente corrette, educate o comprensibili, se non rispondono alla domanda originale.

Esempi di NON_ANSWER:
- "che criterio usi per valutare le mie risposte?"
- "come mi valuti?"
- "quanto mi dai?"
- "che voto mi daresti?"
- "qual è la risposta corretta?"
- "cosa dovrei rispondere?"
- "mi aiuti a rispondere?"
- "puoi farmi un esempio?"
- "puoi spiegarmi la domanda?"
- "non lo so"
- "boh"
- "non saprei"
- "non ho idea"
- "dipende"

REGOLA PRIORITARIA ASSOLUTA:
Se la risposta viene classificata internamente come NON_ANSWER, devi assegnare obbligatoriamente 0 a TUTTI i punteggi:

clarity_score = 0
completeness_score = 0
relevance_score = 0
professionalism_score = 0
synthesis_score = 0
speaking_score = 0
total_score = 0

Non assegnare mai punteggi parziali a una risposta classificata come NON_ANSWER.

In caso di NON_ANSWER:
- feedback deve spiegare che il candidato non ha risposto alla domanda posta;
- improved_answer deve contenere una risposta modello corretta alla domanda originale;
- speaking_feedback deve spiegare che la risposta non è una risposta valida alla domanda;
- solution_explanation deve essere compilata solo se la domanda originale è di logica o richiede un ragionamento passo passo, altrimenti deve essere una stringa vuota.

Valuta la risposta sui seguenti criteri:
1. Chiarezza
2. Completezza
3. Pertinenza rispetto al ruolo e all'azienda
4. Professionalità
5. Sintesi
6. Modo di parlare, solo se sono presenti metriche vocali

Restituisci SOLO un JSON valido, senza testo prima e senza testo dopo.

La struttura deve essere ESATTAMENTE questa:

{{
  "clarity_score": 0,
  "completeness_score": 0,
  "relevance_score": 0,
  "professionalism_score": 0,
  "synthesis_score": 0,
  "speaking_score": 0,
  "total_score": 0,
  "feedback": "feedback dettagliato ma comprensibile",
  "improved_answer": "risposta migliorata o risposta modello alla domanda",
  "speaking_feedback": "feedback sul modo di parlare",
  "solution_explanation": "soluzione spiegata se la domanda è di logica, altrimenti stringa vuota"
}}

Regole di valutazione:
- Tutti i punteggi devono essere numeri interi compresi tra 0 e 100.
- Se la risposta è classificata internamente come NON_ANSWER, tutti i punteggi devono essere 0.
- Se la risposta è incomprensibile, casuale, composta da lettere senza senso o non risponde minimamente alla domanda, assegna 0 a tutti i punteggi.
- Se la risposta è "boh", "non lo so", "chi lo sa", "non saprei" o simili, assegna 0 a tutti i punteggi.
- Se la risposta è completamente fuori tema rispetto alla domanda, assegna 0 a tutti i punteggi.
- Se la risposta fa domande al recruiter, all'intervistatore, all'assistente o all'AI invece di rispondere, assegna 0 a tutti i punteggi.
- Se la risposta chiede informazioni sulla valutazione, sui criteri, sul punteggio, sul codice o sulla logica del sistema, assegna 0 a tutti i punteggi.
- Se la risposta è molto vaga ma contiene almeno un minimo tentativo reale di risposta, assegna punteggi bassi, tra 5 e 20.
- Se la risposta usa un lessico povero, confuso o poco professionale, abbassa clarity_score e professionalism_score.
- Se la risposta non contiene esempi, motivazioni o contenuti concreti, abbassa completeness_score.
- Non premiare una risposta solo perché è lunga: deve essere comprensibile, pertinente e utile.
- Se la risposta è molto prolissa, divaga o contiene molte informazioni non rilevanti, abbassa clarity_score e synthesis_score.
- improved_answer deve essere SEMPRE valorizzata.
- Se il candidato non risponde alla domanda, improved_answer deve contenere una risposta modello corretta alla domanda originale.
- Se la domanda è tecnica, improved_answer deve mostrare una risposta tecnica corretta ma credibile per il livello del candidato.
- Se la domanda è conoscitiva o motivazionale, improved_answer deve mostrare una risposta naturale, professionale e adatta a un colloquio.
- Se la domanda è di logica, improved_answer deve contenere una possibile risposta ragionata e solution_explanation deve contenere la soluzione spiegata passo passo.
- Se la risposta è errata ma la domanda è di logica, spiega comunque il ragionamento corretto in solution_explanation.
- Se sono presenti metriche vocali e la risposta è valida, devi obbligatoriamente valutare il modo di parlare usando quei dati.
- Se sono presenti metriche vocali e la risposta è valida, speaking_score deve essere maggiore di 0.
- Se sono presenti metriche vocali, NON devi mai scrivere che le metriche vocali mancano.
- Nel campo speaking_feedback devi commentare ritmo, chiarezza espositiva, velocità del parlato, parole riempitive e sicurezza percepita.
- Se NON ci sono metriche vocali e la risposta è valida, speaking_score deve essere 0 e speaking_feedback deve dire che la risposta è stata valutata solo sul testo.
- Se la risposta non è valida, speaking_score deve essere 0 anche se sono presenti metriche vocali.
- Non inventare esperienze personali non presenti nella risposta.
- La risposta migliorata deve essere naturale, credibile e coerente con la domanda originale.
- Restituisci solo JSON valido.
"""

    try:
        raw_output = call_groq(prompt, temperature=0.4, max_tokens=1600)
        result = extract_json(raw_output)
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Errore nella valutazione della risposta: {str(e)}"
        )

    clarity_score = clamp_score(result.get("clarity_score", 0))
    completeness_score = clamp_score(result.get("completeness_score", 0))
    relevance_score = clamp_score(result.get("relevance_score", 0))
    professionalism_score = clamp_score(result.get("professionalism_score", 0))
    synthesis_score = clamp_score(result.get("synthesis_score", 0))

    all_textual_scores_are_zero = all(score == 0 for score in [
        clarity_score,
        completeness_score,
        relevance_score,
        professionalism_score,
        synthesis_score
    ])

    if has_speech_metrics:
        speaking_score = clamp_score(result.get("speaking_score", 0))

        # Non trasformare mai lo speaking_score in 60 se il contenuto è già stato valutato 0.
        if all_textual_scores_are_zero:
            speaking_score = 0
        elif speaking_score == 0:
            speaking_score = 60
    else:
        speaking_score = 0

    total_score = compute_total_score(
        clarity_score,
        completeness_score,
        relevance_score,
        professionalism_score,
        synthesis_score,
        speaking_score
    )

    # Se tutti i punteggi testuali sono zero, il totale deve restare zero.
    if all_textual_scores_are_zero:
        total_score = 0
        speaking_score = 0

    feedback = result.get("feedback", "")
    improved_answer = result.get("improved_answer", "")
    solution_explanation = result.get("solution_explanation", "")

    if not improved_answer:
        improved_answer = (
            f"Una risposta migliore alla domanda '{question_text}' dovrebbe rispondere direttamente, "
            "essere chiara, pertinente e includere almeno un esempio o una motivazione concreta."
        )

    if has_speech_metrics:
        speaking_feedback = result.get("speaking_feedback", "")

        invalid_speaking_feedback = (
            not speaking_feedback
            or "non contiene metriche vocali" in speaking_feedback.lower()
            or "non ci sono metriche vocali" in speaking_feedback.lower()
            or "non sono presenti metriche vocali" in speaking_feedback.lower()
            or "valutata solo sul testo" in speaking_feedback.lower()
            or "solo sul contenuto testuale" in speaking_feedback.lower()
        )

        if all_textual_scores_are_zero:
            speaking_feedback = "Il modo di parlare non viene valutato perché la risposta non è valida rispetto alla domanda posta."
        elif invalid_speaking_feedback:
            speaking_feedback = build_speaking_feedback_from_metrics(data.speech_metrics)
    else:
        speaking_feedback = (
            "La risposta è stata valutata solo sul contenuto testuale perché non sono presenti dati sul parlato."
        )

    final_result = {
        "clarity_score": clarity_score,
        "completeness_score": completeness_score,
        "relevance_score": relevance_score,
        "professionalism_score": professionalism_score,
        "synthesis_score": synthesis_score,
        "speaking_score": speaking_score,
        "total_score": total_score,
        "feedback": feedback,
        "improved_answer": improved_answer,
        "speaking_feedback": speaking_feedback,
        "solution_explanation": solution_explanation
    }

    save_answer_result(
        cursor=cursor,
        question_id=question_id,
        user_answer=data.answer,
        result=final_result,
        speech_metrics_json=speech_metrics_json
    )

    cursor.execute("""
    UPDATE interview_sessions
    SET total_score = ?
    WHERE id = ?
    """, (
        total_score,
        session_id
    ))

    conn.commit()
    conn.close()

    print("Valutazione salvata e restituita al frontend.")

    return final_result


# =========================
# ENDPOINT STORICO
# =========================

@app.get("/history/{user_id}")
def get_history(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        s.id,
        s.interview_type,
        s.difficulty,
        s.company,
        s.question_mode,
        s.total_score,
        s.created_at,
        q.question_text,
        a.user_answer,
        a.clarity_score,
        a.completeness_score,
        a.relevance_score,
        a.professionalism_score,
        a.synthesis_score,
        a.speaking_score,
        a.feedback,
        a.improved_answer,
        a.speaking_feedback,
        a.solution_explanation
    FROM interview_sessions s
    JOIN questions q ON q.session_id = s.id
    LEFT JOIN answers a ON a.question_id = q.id
    WHERE s.user_id = ?
    ORDER BY s.created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    history = []

    for row in rows:
        history.append({
            "session_id": row[0],
            "interview_type": row[1],
            "difficulty": row[2],
            "company": row[3],
            "question_mode": row[4],
            "total_score": row[5],
            "created_at": row[6],
            "question": row[7],
            "user_answer": row[8],
            "clarity_score": row[9],
            "completeness_score": row[10],
            "relevance_score": row[11],
            "professionalism_score": row[12],
            "synthesis_score": row[13],
            "speaking_score": row[14],
            "feedback": row[15],
            "improved_answer": row[16],
            "speaking_feedback": row[17],
            "solution_explanation": row[18]
        })

    return history


# =========================
# ENDPOINT PROGRESSI
# =========================

@app.get("/progress/{user_id}")
def get_progress(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        COUNT(a.id),
        AVG(a.total_score),
        AVG(a.clarity_score),
        AVG(a.completeness_score),
        AVG(a.relevance_score),
        AVG(a.professionalism_score),
        AVG(a.synthesis_score),
        AVG(a.speaking_score)
    FROM answers a
    JOIN questions q ON a.question_id = q.id
    JOIN interview_sessions s ON q.session_id = s.id
    WHERE s.user_id = ?
    """, (user_id,))

    row = cursor.fetchone()
    conn.close()

    if not row or row[0] == 0:
        return {
            "message": "Non ci sono ancora risposte valutate per questo utente.",
            "total_answers": 0
        }

    return {
        "total_answers": row[0],
        "average_total_score": round(row[1], 2) if row[1] is not None else 0,
        "average_clarity_score": round(row[2], 2) if row[2] is not None else 0,
        "average_completeness_score": round(row[3], 2) if row[3] is not None else 0,
        "average_relevance_score": round(row[4], 2) if row[4] is not None else 0,
        "average_professionalism_score": round(row[5], 2) if row[5] is not None else 0,
        "average_synthesis_score": round(row[6], 2) if row[6] is not None else 0,
        "average_speaking_score": round(row[7], 2) if row[7] is not None else 0
    }


# =========================
# ENDPOINT FONTI DOMANDA
# =========================

@app.get("/question-sources/{question_id}")
def get_question_sources(question_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        ws.id,
        ws.title,
        ws.url,
        ws.content,
        ws.created_at
    FROM web_sources ws
    JOIN question_web_sources qws ON ws.id = qws.source_id
    WHERE qws.question_id = ?
    ORDER BY ws.created_at DESC
    """, (question_id,))

    rows = cursor.fetchall()
    conn.close()

    sources = []

    for row in rows:
        sources.append({
            "source_id": row[0],
            "title": row[1],
            "url": row[2],
            "content": row[3],
            "created_at": row[4]
        })

    return {
        "question_id": question_id,
        "sources": sources
    }
from fastapi import UploadFile, File
from io import BytesIO
import fitz
from pypdf import PdfReader

@app.post("/debug-cv-read")
async def debug_cv_read(file: UploadFile = File(...)):
    file_bytes = await file.read()

    result = {
        "filename": file.filename,
        "content_type": file.content_type,
        "file_size": len(file_bytes),
        "pymupdf_text_length": 0,
        "pymupdf_preview": "",
        "pypdf_text_length": 0,
        "pypdf_preview": "",
    }

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text_parts = []

        for page in doc:
            page_text = page.get_text("text")
            if page_text:
                text_parts.append(page_text)

        doc.close()

        pymupdf_text = "\n".join(text_parts).strip()
        result["pymupdf_text_length"] = len(pymupdf_text)
        result["pymupdf_preview"] = pymupdf_text[:1000]

    except Exception as e:
        result["pymupdf_error"] = str(e)

    try:
        reader = PdfReader(BytesIO(file_bytes))
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        pypdf_text = "\n".join(text_parts).strip()
        result["pypdf_text_length"] = len(pypdf_text)
        result["pypdf_preview"] = pypdf_text[:1000]

    except Exception as e:
        result["pypdf_error"] = str(e)

    return result
