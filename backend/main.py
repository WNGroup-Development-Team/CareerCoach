import os
import json
import sqlite3
import requests
from typing import Optional, List, Dict

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

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

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
    education: str
    target_role: str
    sector: str
    experience_level: str
    interview_language: str = "Italiano"


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


def is_zero_answer(answer: str, question: str = "") -> bool:
    """
    Riconosce risposte che devono prendere 0:
    - lettere casuali;
    - risposta vuota;
    - 'boh', 'non lo so', 'chi lo sa';
    - risposta troppo corta;
    - risposta evidentemente non pertinente.
    """

    if not answer:
        return True

    text = answer.strip().lower()

    if len(text) < 3:
        return True

    zero_phrases = [
        "boh",
        "non lo so",
        "non so",
        "chi lo sa",
        "bo",
        "mah",
        "non ne ho idea",
        "nessuna idea",
        "non saprei",
        "non mi viene",
        "non mi viene in mente",
        "non voglio rispondere",
        "skip",
        "passo",
        "idk",
        "i don't know",
        "dont know",
        "no idea"
    ]

    if text in zero_phrases:
        return True

    for phrase in zero_phrases:
        if phrase in text and len(text.split()) <= 6:
            return True

    words = text.split()

    if len(words) < 3:
        return True

    vowels = "aeiouàèéìòù"
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
        return True

    letters = sum(1 for ch in text if ch.isalpha())
    total = len(text)

    if total > 0 and letters / total < 0.45:
        return True

    irrelevant_short_answers = [
        "ciao",
        "ok",
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
        "non mi piace"
    ]

    if text in irrelevant_short_answers:
        return True

    return False


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

    if is_zero_answer(data.answer, question_text):
        zero_result = build_zero_feedback(
            reason="Risposta indecifrabile, non pertinente o priva di contenuto utile",
            question=question_text,
            interview_type=interview_type
        )

        speech_metrics_json = None

        if data.speech_metrics:
            try:
                speech_metrics_json = data.speech_metrics.model_dump_json()
            except Exception:
                speech_metrics_json = data.speech_metrics.json()

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
            data.answer,
            zero_result["clarity_score"],
            zero_result["completeness_score"],
            zero_result["relevance_score"],
            zero_result["professionalism_score"],
            zero_result["synthesis_score"],
            zero_result["speaking_score"],
            zero_result["total_score"],
            zero_result["feedback"],
            zero_result["improved_answer"],
            zero_result["speaking_feedback"],
            zero_result["solution_explanation"],
            speech_metrics_json
        ))

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

Valuta la risposta secondo questi criteri:
1. Chiarezza
2. Completezza
3. Pertinenza rispetto al ruolo e all'azienda
4. Professionalità
5. Sintesi
6. Modo di parlare, se sono presenti metriche vocali

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
- Se la risposta è incomprensibile, casuale, composta da lettere senza senso o non risponde minimamente alla domanda, assegna 0 a tutti i punteggi.
- Se la risposta è "boh", "non lo so", "chi lo sa", "non saprei" o simili, assegna 0 a tutti i punteggi.
- Se la risposta è completamente fuori tema rispetto alla domanda, assegna 0 a pertinenza e un total_score molto basso, massimo 10.
- Se la risposta è molto vaga ma contiene almeno un minimo di senso, assegna punteggi bassi, tra 5 e 20.
- Se la risposta usa un lessico povero, confuso o poco professionale, abbassa chiarezza e professionalità.
- Se la risposta non contiene esempi, motivazioni o contenuti concreti, abbassa completezza.
- Non premiare una risposta solo perché è lunga: deve essere comprensibile, pertinente e utile.
- improved_answer deve essere SEMPRE valorizzata.
- Se il candidato non risponde alla domanda, improved_answer deve contenere una risposta modello corretta alla domanda.
- Se la domanda è tecnica, improved_answer deve mostrare una risposta tecnica corretta ma credibile per il livello del candidato.
- Se la domanda è conoscitiva/motivazionale, improved_answer deve mostrare una risposta naturale, professionale e adatta a un colloquio.
- Se la domanda è di logica, improved_answer deve contenere una possibile risposta ragionata e solution_explanation deve contenere la soluzione spiegata passo passo.
- Se la risposta è errata ma la domanda è di logica, spiega comunque il ragionamento corretto.
- Se sono presenti metriche vocali, devi obbligatoriamente valutare il modo di parlare usando quei dati.
- Se sono presenti metriche vocali, NON devi mai scrivere che le metriche vocali mancano.
- Se sono presenti metriche vocali, speaking_score deve essere maggiore di 0, salvo casi di risposta indecifrabile o completamente non valida.
- Nel campo speaking_feedback devi commentare ritmo, chiarezza espositiva, velocità del parlato, parole riempitive e sicurezza percepita.
- Se NON ci sono metriche vocali, speaking_score deve essere 0 e speaking_feedback deve dire che la risposta è stata valutata solo sul testo.
- Non inventare esperienze personali non presenti nella risposta.
- La risposta migliorata deve essere naturale e credibile.
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

    if has_speech_metrics:
        speaking_score = clamp_score(result.get("speaking_score", 0))

        if speaking_score == 0:
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

        if invalid_speaking_feedback:
            speaking_feedback = build_speaking_feedback_from_metrics(data.speech_metrics)
    else:
        speaking_feedback = "La risposta è stata valutata solo sul contenuto testuale perché non sono presenti dati sul parlato."

    speech_metrics_json = None

    if data.speech_metrics:
        try:
            speech_metrics_json = data.speech_metrics.model_dump_json()
        except Exception:
            speech_metrics_json = data.speech_metrics.json()

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
        data.answer,
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

    print("Valutazione salvata e restituita al frontend.")

    return {
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