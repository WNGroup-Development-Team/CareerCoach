## CareerCoach - Descrizione tecnica

CareerCoach è una web application che supporta gli utenti nella preparazione ai colloqui di lavoro e nell’ottimizzazione del curriculum.

### Architettura

L’applicazione è composta da:

- **Frontend React**, responsabile dell’interfaccia e del flusso utente.
- **Backend FastAPI**, che espone API REST e gestisce la logica applicativa.
- **Database SQLite**, utilizzato per profili, sessioni, risposte, CV e risultati.
- **Servizi AI**, utilizzati per generare domande, valutare risposte e migliorare il CV.

### Funzionalità principali

**Simulazione dei colloqui**

L’utente seleziona ruolo, azienda, tipologia e difficoltà del colloquio. Il backend genera domande personalizzate utilizzando il profilo dell’utente, eventuali fonti web e un modello linguistico.

Le risposte vengono valutate secondo:

- chiarezza;
- completezza;
- pertinenza;
- professionalità;
- capacità di sintesi;
- qualità del parlato.

Il sistema restituisce punteggi, feedback, una risposta migliorata e, per le domande logiche, la spiegazione del ragionamento corretto.

**Analisi del parlato**

Il frontend può acquisire la risposta tramite microfono e calcola:

- durata;
- numero di parole;
- velocità in parole al minuto;
- parole riempitive.

Questi dati vengono inviati al backend e integrati nella valutazione.

**Ottimizzazione del CV**

Il sistema accetta CV PDF o DOCX, ne estrae il testo e lo confronta con il ruolo o l’offerta di lavoro target.

La pipeline:

1. riconosce le sezioni del CV;
2. estrae keyword e competenze richieste;
3. confronta requisiti e contenuto del curriculum;
4. individua punti di forza, lacune e problemi ATS;
5. genera suggerimenti puntuali;
6. applica esclusivamente le modifiche accettate o confermate dall’utente;
7. esporta il risultato in DOCX e, quando disponibile, PDF.

Sono presenti controlli per evitare l’inserimento di competenze o esperienze non confermate e per preservare la struttura originale del documento.

### Tecnologie

- **React 19**
- **Vite 8**
- **JavaScript**
- **FastAPI**
- **Python**
- **Pydantic**
- **SQLite**
- **Groq API / modelli LLM**
- **Tavily API**
- **python-docx**
- **PyMuPDF**
- **pypdf**
- **Uvicorn**
- **OAuth e autenticazione tramite token**

### Persistenza

SQLite memorizza:

- utenti e profili;
- sessioni di autenticazione;
- sessioni di colloquio;
- domande e fonti;
- risposte e punteggi;
- CV originali;
- CV ottimizzati;
- analisi della presenza digitale.

### Logica generale

Il frontend mantiene lo stato del percorso dell’utente e comunica con il backend tramite API REST. FastAPI valida le richieste, applica le regole applicative, interroga i servizi AI e salva i risultati nel database.

L’AI non prende completamente il controllo del processo: il codice contiene validazioni deterministiche, fallback locali e controlli di sicurezza. In particolare, le risposte non pertinenti ricevono punteggio zero e le modifiche al CV devono essere supportate dal contenuto originale o confermate dall’utente.

# Setup progetto CareerCoach

## 1. Clonare il repository

```bash
git clone URL_DEL_REPOSITORY
cd careercoach
```

La struttura del progetto deve essere circa così:

```text
careercoach/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   └── careercoach.db   ← si crea automaticamente
│
└── frontend/
    ├── package.json
    ├── src/
    │   ├── App.jsx
    │   └── App.css
```

---

# 2. Configurare il backend

Entrare nella cartella backend:

```bash
cd backend
```

Creare l’ambiente virtuale:

```bash
python -m venv venv
```

Attivarlo.

Su Windows PowerShell:

```bash
venv\Scripts\Activate.ps1
```

Se PowerShell blocca l’attivazione:

```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Poi riprovare:

```bash
venv\Scripts\Activate.ps1
```

Installare le librerie:

```bash
pip install -r requirements.txt
```

---

# 3. Creare il file `.env`

Dentro `backend/`, creare un file chiamato:

```text
.env
```

Il file deve contenere:

```env
GROQ_API_KEY=INSERISCI_LA_CHIAVE_GROQ
GROQ_MODEL=llama-3.1-8b-instant

TAVILY_API_KEY=INSERISCI_LA_CHIAVE_TAVILY
```

Le chiavi servono a:

```text
GROQ_API_KEY  → generazione domande e valutazione risposte
TAVILY_API_KEY → ricerca online di domande/esperienze di colloquio
```

Il file `.env` **non deve essere caricato su GitHub**.

Conviene invece creare un file:

```text
.env.example
```

con dentro:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant

TAVILY_API_KEY=your_tavily_api_key_here
```

---

# 4. Avviare il backend

Sempre dentro `backend`, con il virtual environment attivo:

```bash
uvicorn main:app --reload --reload-exclude "test_*.py" --reload-exclude "*debug*"
```

Se tutto funziona, compare:

```text
Uvicorn running on http://127.0.0.1:8000
```

Per controllare:

```text
http://127.0.0.1:8000
```

Per testare le API:

```text
http://127.0.0.1:8000/docs
```

---

# 5. Configurare il frontend

Aprire un secondo terminale.

Dalla cartella principale del progetto:

```bash
cd frontend
```

Installare le dipendenze:

```bash
npm install
```

Avviare il frontend:

```bash
npm run dev
```

Se tutto funziona, compare un link tipo:

```text
http://localhost:5173
```

Aprirlo nel browser.

---

# 6. Avviare tutto insieme

Per usare l’app devono essere attivi **due terminali**.

## Terminale 1 — Backend

```bash
cd backend
venv\Scripts\Activate.ps1
uvicorn main:app --reload --reload-exclude "test_*.py" --reload-exclude "*debug*"
```

Backend:

```text
http://127.0.0.1:8000
```

## Terminale 2 — Frontend

```bash
cd frontend
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 7. File da non caricare su GitHub

Nel file `.gitignore` devono esserci almeno:

```gitignore
# Python
backend/venv/
backend/__pycache__/
backend/*.pyc

# Database locale
backend/careercoach.db

# Env
backend/.env
.env

# Node
frontend/node_modules/
frontend/dist/
```

---

# 8. Comandi rapidi

## Prima installazione

```bash
git clone URL_DEL_REPOSITORY
cd careercoach
```

Backend:

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --reload-exclude "test_*.py" --reload-exclude "*debug*"
```

Frontend, in un altro terminale:

```bash
cd frontend
npm install
npm run dev
```

---

# 9. Test consigliato dopo l’avvio

Aprire:

```text
http://127.0.0.1:8000/docs
```

Testare in ordine:

```text
1. GET /
2. POST /users
3. POST /generate-question
4. POST /evaluate-answer
5. GET /history/{user_id}
6. GET /progress/{user_id}
```

Poi aprire:

```text
http://localhost:5173
```

e provare il flusso completo:

```text
crea profilo → scegli azienda → genera domanda → rispondi → ricevi feedback
```

---

# 10. Dipendenze necessarie sul PC

Ogni collega deve avere installato:

```text
Python 3.10 o superiore
Node.js
npm
Visual Studio Code, consigliato
```
