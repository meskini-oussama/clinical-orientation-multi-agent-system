# 🏥 Système d'Orientation Clinique Simulée — Multi-Agents avec LangGraph

> ⚠️ **Avertissement éthique :** Ce système est un exercice académique (Module SMA).
> Il ne constitue pas un dispositif médical et ne fournit aucun diagnostic définitif.
> **« Ce système ne remplace pas une consultation médicale. »**

---

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-green)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40%2B-FF4B4B?logo=streamlit)](https://streamlit.io)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-orange)](https://github.com/anthropics/mcp)

## 📋 Présentation

Application multi-agents simulant un **workflow d'orientation clinique préliminaire** :

1. **Interrogatoire structuré** : le DiagnosticAgent pose 5 questions au patient fictif.
2. **Synthèse clinique** : le LLM produit une orientation clinique préliminaire.
3. **Validation médecin** : étape Human-in-the-Loop obligatoire.
4. **Rapport final** : le ReportAgent génère un rapport structuré horodaté.

### Stack technique

| Composant | Technologie | Rôle |
|---|---|---|
| Orchestration | LangGraph 0.2+ | Graphe d'agents + interruptions HITL |
| LLM | Groq / OpenAI / Anthropic | Inférence (configurable) |
| Backend API | FastAPI + Uvicorn | 5 endpoints REST |
| Protocole outils | MCP (FastMCP) | Directives médicales + logging |
| Frontend | Streamlit | Interface 4 écrans |
| Persistance | MemorySaver (LangGraph) | État en mémoire (dev) |

---

## 🔧 Prérequis

### Environnement système

- **Python 3.10 ou supérieur** (testé sur 3.10, 3.11, 3.12)
- **pip** (>= 23.0 recommandé)
- **Git**
- Connexion internet (pour les appels API LLM)

### Clé API LLM

Vous devez disposer d'au moins **une** des clés suivantes :

| Fournisseur | Obtenir une clé | Gratuit ? |
|---|---|---|
| **Groq** (recommandé) | [console.groq.com](https://console.groq.com) | ✅ Plan gratuit |
| OpenAI | [platform.openai.com](https://platform.openai.com) | 💳 Payant |
| Anthropic | [console.anthropic.com](https://console.anthropic.com) | 💳 Payant |

### Vérification de la version Python

```bash
python --version
# ou
python3 --version
# Doit afficher Python 3.10.x ou supérieur
```

---

## 🚀 Installation

### Étape 1 — Cloner le dépôt

```bash
git clone https://github.com/<votre-username>/medical-multiagent-sma.git
cd medical-multiagent-sma
```

### Étape 2 — Créer l'environnement virtuel

```bash
# Création du venv
python -m venv venv

# Activation — Linux / macOS
source venv/bin/activate

# Activation — Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activation — Windows (cmd)
venv\Scripts\activate.bat
```

Votre prompt doit afficher `(venv)` pour confirmer l'activation.

### Étape 3 — Installer les dépendances

```bash
# Installer toutes les dépendances (backend + frontend + MCP)
pip install -r backend/requirements.txt

# Si vous utilisez Groq (recommandé), ajouter :
pip install langchain-groq
```

> **Note :** L'installation complète prend environ 2-3 minutes selon votre connexion.

### Étape 4 — Configurer les variables d'environnement

Créez un fichier `.env` à la racine du projet `backend/` :

```bash
# Depuis la racine du projet
cp backend/.env.example backend/.env
# ou créez-le manuellement :
touch backend/.env
```

Éditez `backend/.env` avec votre éditeur :

```env
# ── Fournisseur LLM ───────────────────────────────────────────────
# Options : groq | openai | anthropic
LLM_PROVIDER=groq

# ── Groq (recommandé — gratuit) ───────────────────────────────────
GROQ_API_KEY=gsk_VOTRE_CLE_GROQ_ICI
GROQ_MODEL=llama-3.3-70b-versatile

# ── OpenAI (optionnel) ────────────────────────────────────────────
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-VOTRE_CLE_OPENAI_ICI
# OPENAI_MODEL=gpt-4o

# ── Anthropic (optionnel) ─────────────────────────────────────────
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-VOTRE_CLE_ANTHROPIC_ICI
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### Étape 5 — Vérifier la structure

```bash
# Vérifiez que tous les fichiers sont présents
ls backend/app/
# Attendu : __init__.py  api.py  graph.py  mcp_client.py  state.py  tools/

ls mcp_server/
# Attendu : server.py  data/

ls frontend/
# Attendu : app.py
```

---

## ▶️ Lancement du système

Le système nécessite **3 terminaux** ouverts simultanément. Suivez l'ordre indiqué.

### Terminal 1 — Serveur MCP

```bash
# Depuis la racine du projet
source venv/bin/activate   # ou .\venv\Scripts\activate sur Windows

python mcp_server/server.py
```

**Sortie attendue :**
```
🏥 Démarrage du serveur MCP d'orientation clinique simulée...
📁 Répertoire de données : /path/to/project/mcp_server/data
⚠️  RAPPEL : Ce système est un exercice académique.
     « Ce système ne remplace pas une consultation médicale. »
────────────────────────────────────────────────────────────────
```

Laissez ce terminal ouvert. Le serveur MCP tourne en mode `stdio` et sera appelé par le backend lors des invocations des outils.

> **Note :** Si le serveur MCP n'est pas lancé, les outils MCP utiliseront leur fallback Python interne et le workflow continuera normalement.

### Terminal 2 — Backend FastAPI

```bash
# Depuis la racine du projet
source venv/bin/activate

cd backend
uvicorn app.api:app --reload --port 8000 --host 0.0.0.0
```

**Sortie attendue :**
```
INFO:     Will watch for changes in these directories: ['/path/to/backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXXX] using WatchFiles
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Vérifiez que l'API fonctionne :
```bash
curl http://localhost:8000/health
# Attendu : {"status":"healthy","graph_loaded":true,...}
```

📖 Documentation Swagger disponible sur : **http://localhost:8000/docs**

### Terminal 3 — Frontend Streamlit

```bash
# Depuis la racine du projet
source venv/bin/activate

streamlit run frontend/app.py --server.port 8501
```

**Sortie attendue :**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

L'interface s'ouvre automatiquement dans votre navigateur sur **http://localhost:8501**

---

## 🧪 Test rapide (API directe)

Vous pouvez tester le workflow complet via `curl` sans le frontend :

```bash
# 1. Créer une session
SESSION=$(curl -s -X POST http://localhost:8000/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"patient_alias": "Test Patient"}')
echo $SESSION
THREAD_ID=$(echo $SESSION | python3 -c "import sys,json; print(json.load(sys.stdin)['thread_id'])")
echo "Thread ID: $THREAD_ID"

# 2. Démarrer la consultation
curl -s -X POST http://localhost:8000/consultation/start \
  -H "Content-Type: application/json" \
  -d "{\"thread_id\": \"$THREAD_ID\", \"patient_info\": \"Patient de 30 ans, toux sèche depuis 3 jours, légère fièvre.\"}" | python3 -m json.tool

# 3. Répondre aux 5 questions (à répéter 5 fois)
curl -s -X POST http://localhost:8000/consultation/resume \
  -H "Content-Type: application/json" \
  -d "{\"thread_id\": \"$THREAD_ID\", \"resume_type\": \"patient_answer\", \"content\": \"J'ai une toux sèche et de la fièvre à 38°C depuis 3 jours.\"}" | python3 -m json.tool

# (Répétez avec vos réponses pour Q2, Q3, Q4, Q5)

# 4. Valider avec l'avis du médecin (après les 5 réponses)
curl -s -X POST http://localhost:8000/consultation/resume \
  -H "Content-Type: application/json" \
  -d "{\"thread_id\": \"$THREAD_ID\", \"resume_type\": \"physician_review\", \"content\": \"Prescription paracétamol 1g x3/j, repos 48h, réévaluation si aggravation.\"}" | python3 -m json.tool

# 5. Récupérer le rapport final
curl -s http://localhost:8000/consultation/$THREAD_ID/report | python3 -m json.tool
```

---

## 🎨 Test dans LangGraph Studio

### Configuration

LangGraph Studio permet de visualiser le graphe, inspecter les états intermédiaires et rejouer les étapes.

**Prérequis :** [Télécharger LangGraph Studio](https://github.com/langchain-ai/langgraph-studio/releases)

### Étapes

**1. Ouvrir le projet dans LangGraph Studio**

Lancez LangGraph Studio et ouvrez le dossier `backend/`. Le fichier `langgraph.json` sera détecté automatiquement :

```json
{
  "dependencies": ["."],
  "graphs": {
    "medical_workflow": "./app/graph.py:medical_graph"
  },
  "env": ".env"
}
```

**2. Vérifier les variables d'environnement**

LangGraph Studio charge automatiquement le fichier `.env` spécifié dans `langgraph.json`. Vérifiez que `backend/.env` contient votre clé API.

**3. Visualiser le graphe**

Dans l'onglet **Graph**, vous devez voir les nœuds :
```
START → supervisor → diagnostic_agent → supervisor → physician_review → supervisor → report_agent → supervisor → END
```

Les nœuds `diagnostic_agent` et `physician_review` sont marqués comme points d'interruption (⏸️).

**4. Lancer un test interactif**

Dans l'onglet **Run**, saisissez l'état initial :

```json
{
  "patient_info": "Patient de 35 ans, toux sèche depuis 4 jours, fièvre 38°C, légère rhinorrhée.",
  "session_id": "studio-test-001",
  "messages": [],
  "question_count": 0,
  "patient_answers": [],
  "awaiting_patient": false,
  "interim_care": "",
  "diagnostic_summary": "",
  "physician_treatment": "",
  "final_report": ""
}
```

Cliquez sur **Run**. Le graphe s'exécute jusqu'à la première interruption.

**5. Injecter les réponses patient**

À chaque interruption `diagnostic_agent`, utilisez **Update State** pour injecter :

```json
{
  "patient_answers": ["Ma réponse à la question 1"],
  "awaiting_patient": false
}
```

Cliquez **Continue** pour reprendre.

**6. Injecter l'avis du médecin**

À l'interruption `physician_review`, injectez :

```json
{
  "physician_treatment": "Paracétamol 1g x3/j, repos 72h, réévaluation si fièvre persistante."
}
```

**7. Observer le rapport final**

Après la dernière reprise, inspectez le champ `final_report` dans le panneau d'état. Il doit contenir le rapport complet avec le disclaimer éthique.

---

## 📁 Structure complète du projet

```
project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── state.py           # MedicalState (TypedDict)
│   │   ├── graph.py           # LangGraph (4 nœuds + interruptions)
│   │   ├── api.py             # FastAPI (5 endpoints)
│   │   ├── mcp_client.py      # Client MCP → LangChain tools
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── patient_tools.py  # ask_patient (5 questions)
│   │       └── care_tools.py     # recommend_interim_care
│   ├── .env                   # Variables d'environnement (à créer)
│   ├── langgraph.json         # Config LangGraph Studio
│   └── requirements.txt
├── mcp_server/
│   ├── server.py              # FastMCP (3 outils + 2 ressources)
│   └── data/                  # Logs JSON des sessions
├── frontend/
│   └── app.py                 # Streamlit (4 écrans)
├── docs/
│   ├── RAPPORT_TECHNIQUE.md
│   └── GUIDE_DEMONSTRATION.md
└── README.md
```

---

## 🔍 Dépannage

### Le backend ne démarre pas

```bash
# Vérifier que le venv est activé
which python  # doit pointer vers venv/bin/python

# Vérifier les imports
cd backend
python -c "from app.graph import medical_graph; print('OK')"
```

### Erreur "API Key not found"

```bash
# Vérifier que .env est dans backend/
cat backend/.env

# Vérifier que la variable est bien lue
cd backend
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print(os.getenv('GROQ_API_KEY', 'NOT FOUND'))"
```

### Le frontend ne se connecte pas au backend

```bash
# Vérifier que le backend écoute bien
curl http://localhost:8000/health

# Si l'erreur persiste, vérifier le port dans frontend/app.py
grep "API_BASE" frontend/app.py
# Doit afficher : API_BASE = "http://localhost:8000"
```

### Les questions s'enchaînent trop vite (ancien bug)

Ce bug a été corrigé dans la v2 du graphe. Vérifiez que vous utilisez bien la dernière version de `graph.py` qui contient `interrupt_before=["diagnostic_agent", "physician_review"]` :

```bash
grep "interrupt_before" backend/app/graph.py
# Doit afficher : interrupt_before=["diagnostic_agent", "physician_review"],
```

---

## 📦 Dépendances principales

```
langgraph>=0.2.0          # Orchestration multi-agents
langchain>=0.3.0          # Framework LLM
langchain-groq            # Intégration Groq (recommandé)
langchain-openai>=0.2.0   # Intégration OpenAI
fastapi>=0.115.0          # API REST
uvicorn[standard]>=0.30.0 # Serveur ASGI
mcp>=1.0.0                # Model Context Protocol
streamlit>=1.40.0         # Interface utilisateur
pydantic>=2.0.0           # Validation des données
python-dotenv>=1.0.0      # Variables d'environnement
```

---

## 🏫 Informations académiques

- **Module :** Système Multi-Agents (SMA)
- **Encadrant :** Pr. MHAMMEDI Sajida
- **Institution :** École Nationale de l'Intelligence Artificielle et du Digital, Berkane
- **Université :** Mohammed Premier, Oujda

---

**« Ce système ne remplace pas une consultation médicale. »**