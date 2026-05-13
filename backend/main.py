import os
import json
import sqlite3
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel


# =========================
# CONFIGURAZIONE AMBIENTE
# =========================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

if not GROQ_API_KEY:
    raise RuntimeError("Manca GROQ_API_KEY nel file .env")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


# =========================
# APP FASTAPI
# =========================

app = FastAPI(title="CareerCoach API")


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
        total_score INTEGER,
        feedback TEXT,
        improved_answer TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(question_id) REFERENCES questions(id)
    )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# MODELLI PYDANTIC
# =========================

class UserCreate(BaseModel):
    name: str
    email: Optional[str] = None
    education: str
    target_role: str
    sector: str
    experience_level: str
    interview_language: str = "Italiano"


class GenerateQuestionRequest(BaseModel):
    user_id: int
    interview_type: str
    difficulty: str = "intermedio"


class EvaluateAnswerRequest(BaseModel):
    question_id: int
    answer: str


# =========================
# FUNZIONE AI GROQCLOUD
# =========================

def call_ai(prompt: str, temperature: float = 0.7, max_tokens: int = 1000) -> str:
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un assistente esperto nella preparazione ai colloqui "
                        "di lavoro. Devi dare risposte utili, concrete e adatte "
                        "a studenti, neolaureati e candidati junior."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante la chiamata a GroqCloud: {str(e)}"
        )


def extract_json(text: str):
    """
    Estrae un JSON valido anche se il modello lo restituisce dentro:
    ```json
    { ... }
    ```
    """

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
            json_text = text[start:end]
            return json.loads(json_text)

        raise ValueError(f"JSON non valido restituito dal modello: {text}")


# =========================
# ENDPOINT BASE
# =========================

@app.get("/")
def home():
    return {
        "message": "CareerCoach backend attivo con GroqCloud",
        "model": GROQ_MODEL
    }


# =========================
# ENDPOINT UTENTI
# =========================

@app.post("/users")
def create_user(data: UserCreate):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (
        name,
        email,
        education,
        target_role,
        sector,
        experience_level,
        interview_language
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.name,
        data.email,
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
        interview_language
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
        "interview_language": row[7]
    }


# =========================
# ENDPOINT GENERA DOMANDA
# =========================

@app.post("/generate-question")
def generate_question(data: GenerateQuestionRequest):
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

    prompt = f"""
Sei un recruiter esperto e stai aiutando una persona ad allenarsi per un colloquio di lavoro.

Profilo candidato:
- Nome: {name}
- Percorso di studi: {education}
- Ruolo target: {target_role}
- Settore: {sector}
- Livello esperienza: {experience_level}
- Lingua colloquio: {interview_language}

Tipo di colloquio:
{data.interview_type}

Difficoltà:
{data.difficulty}

Genera UNA SOLA domanda di colloquio.

Regole:
- La domanda deve essere realistica.
- La domanda deve essere coerente con il ruolo target.
- La domanda deve essere adatta al livello di esperienza.
- Non aggiungere spiegazioni.
- Non numerare la domanda.
- Scrivi solo la domanda.
"""

    try:
        question_text = call_ai(prompt, temperature=0.7, max_tokens=300)
    except Exception as e:
        conn.close()
        raise e

    cursor.execute("""
    INSERT INTO interview_sessions (
        user_id,
        interview_type,
        difficulty
    )
    VALUES (?, ?, ?)
    """, (
        user_id,
        data.interview_type,
        data.difficulty
    ))

    session_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO questions (
        session_id,
        question_text,
        category,
        difficulty
    )
    VALUES (?, ?, ?, ?)
    """, (
        session_id,
        question_text,
        data.interview_type,
        data.difficulty
    ))

    question_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "session_id": session_id,
        "question_id": question_id,
        "question": question_text
    }


# =========================
# ENDPOINT VALUTA RISPOSTA
# =========================

@app.post("/evaluate-answer")
def evaluate_answer(data: EvaluateAnswerRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        q.id,
        q.question_text,
        q.session_id,
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

    prompt = f"""
Sei un coach esperto di colloqui di lavoro.

Devi valutare la risposta di un candidato a una domanda di colloquio.

Profilo candidato:
- Nome: {name}
- Percorso di studi: {education}
- Ruolo target: {target_role}
- Settore: {sector}
- Livello esperienza: {experience_level}
- Lingua colloquio: {interview_language}

Tipo di colloquio:
{interview_type}

Difficoltà:
{difficulty}

Domanda del colloquio:
{question_text}

Risposta del candidato:
{data.answer}

Valuta la risposta secondo questi criteri:

1. Chiarezza:
La risposta è comprensibile, ordinata e facile da seguire?

2. Completezza:
La risposta risponde davvero alla domanda oppure rimane troppo generica?

3. Pertinenza:
La risposta è coerente con il ruolo target e con il settore scelto?

4. Professionalità:
Il tono è adatto a un colloquio di lavoro?

5. Sintesi:
La risposta è della lunghezza giusta oppure è troppo breve/troppo lunga?

Restituisci SOLO un JSON valido, senza testo prima e senza testo dopo.

La struttura deve essere ESATTAMENTE questa:

{{
  "clarity_score": 0,
  "completeness_score": 0,
  "relevance_score": 0,
  "professionalism_score": 0,
  "synthesis_score": 0,
  "total_score": 0,
  "feedback": "feedback dettagliato ma comprensibile",
  "improved_answer": "risposta migliorata adatta a un colloquio"
}}

Regole obbligatorie:
- I punteggi devono essere numeri interi da 0 a 100.
- Il total_score deve essere la media ragionata dei cinque criteri.
- Il feedback deve spiegare cosa funziona e cosa migliorare.
- La risposta migliorata deve mantenere un tono naturale.
- Non devi inventare esperienze non presenti nella risposta, ma puoi valorizzare meglio ciò che il candidato ha scritto.
- Se la risposta è troppo generica, spiega cosa andrebbe aggiunto.
- Restituisci solo JSON valido.
"""

    try:
        raw_output = call_ai(prompt, temperature=0.4, max_tokens=1200)
        result = extract_json(raw_output)

    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Errore nella valutazione della risposta: {str(e)}"
        )

    clarity_score = result.get("clarity_score", 0)
    completeness_score = result.get("completeness_score", 0)
    relevance_score = result.get("relevance_score", 0)
    professionalism_score = result.get("professionalism_score", 0)
    synthesis_score = result.get("synthesis_score", 0)
    total_score = result.get("total_score", 0)
    feedback = result.get("feedback", "")
    improved_answer = result.get("improved_answer", "")

    cursor.execute("""
    INSERT INTO answers (
        question_id,
        user_answer,
        clarity_score,
        completeness_score,
        relevance_score,
        professionalism_score,
        synthesis_score,
        total_score,
        feedback,
        improved_answer
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        question_id,
        data.answer,
        clarity_score,
        completeness_score,
        relevance_score,
        professionalism_score,
        synthesis_score,
        total_score,
        feedback,
        improved_answer
    ))

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

    return {
        "clarity_score": clarity_score,
        "completeness_score": completeness_score,
        "relevance_score": relevance_score,
        "professionalism_score": professionalism_score,
        "synthesis_score": synthesis_score,
        "total_score": total_score,
        "feedback": feedback,
        "improved_answer": improved_answer
    }


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
        s.total_score,
        s.created_at,
        q.question_text,
        a.user_answer,
        a.clarity_score,
        a.completeness_score,
        a.relevance_score,
        a.professionalism_score,
        a.synthesis_score,
        a.feedback,
        a.improved_answer
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
            "total_score": row[3],
            "created_at": row[4],
            "question": row[5],
            "user_answer": row[6],
            "clarity_score": row[7],
            "completeness_score": row[8],
            "relevance_score": row[9],
            "professionalism_score": row[10],
            "synthesis_score": row[11],
            "feedback": row[12],
            "improved_answer": row[13]
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
        AVG(a.synthesis_score)
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
        "average_synthesis_score": round(row[6], 2) if row[6] is not None else 0
    }