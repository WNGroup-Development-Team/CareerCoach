
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
uvicorn main:app --reload
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
uvicorn main:app --reload
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
uvicorn main:app --reload
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
