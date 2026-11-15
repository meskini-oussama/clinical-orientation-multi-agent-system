"""
frontend/app.py — Interface Streamlit du Système d'Orientation Clinique Simulée

4 écrans requis :
    Écran 1 : Saisie du cas patient initial
    Écran 2 : Questions / Réponses patient (DiagnosticAgent × 5)
    Écran 3 : Revue du médecin traitant (Human-in-the-Loop)
    Écran 4 : Rapport final structuré

100% compatible avec backend/app/api.py (SessionStartResponse,
ConsultationStartRequest, ConsultationResumeRequest, etc.)

Lancement :
    streamlit run frontend/app.py
"""

import time
import requests
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Système d'Orientation Clinique Simulée",
    layout="wide",
    initial_sidebar_state="expanded"  
)

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — CSS global
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* ── Google Fonts ─────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Variables ────────────────────────────────────────────────── */
:root {
    --navy:      #0a1628;
    --navy-mid:  #0f2040;
    --navy-soft: #1a3055;
    --teal:      #00c9a7;
    --teal-dim:  #00a88a;
    --gold:      #f5c842;
    --rose:      #ff6b6b;
    --slate:     #8da0b3;
    --white:     #f0f4f8;
    --card-bg:   rgba(15, 32, 64, 0.85);
    --border:    rgba(0, 201, 167, 0.18);
    --radius:    14px;
    --shadow:    0 8px 32px rgba(0,0,0,0.35);
}

/* ── Base ─────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background: var(--navy);
    color: var(--white);
}

.main .block-container {
    padding: 2rem 3rem 4rem;
    max-width: 960px;
    margin: 0 auto;
}

/* ── Header bar ───────────────────────────────────────────────── */
.app-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.4rem 2rem;
    background: linear-gradient(135deg, var(--navy-mid) 0%, #0d2545 100%);
    border-bottom: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 2rem;
}
.app-header .logo {
    font-size: 2.2rem;
    line-height: 1;
}
.app-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 1.55rem;
    font-weight: 400;
    color: var(--white);
    margin: 0;
    letter-spacing: -0.01em;
}
.app-header .subtitle {
    font-size: 0.78rem;
    color: var(--slate);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 2px;
}

/* ── Progress stepper ─────────────────────────────────────────── */
.stepper {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin-bottom: 2.5rem;
    padding: 0 1rem;
}
.step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    flex: 1;
    position: relative;
}
.step-item:not(:last-child)::after {
    content: '';
    position: absolute;
    top: 18px;
    left: calc(50% + 18px);
    width: calc(100% - 36px);
    height: 2px;
    background: var(--border);
}
.step-item.done:not(:last-child)::after { background: var(--teal); }
.step-circle {
    width: 36px; height: 36px;
    border-radius: 50%;
    background: var(--navy-soft);
    border: 2px solid var(--border);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 600;
    color: var(--slate);
    position: relative; z-index: 1;
    transition: all 0.3s ease;
}
.step-item.active .step-circle {
    background: var(--teal);
    border-color: var(--teal);
    color: var(--navy);
    box-shadow: 0 0 0 6px rgba(0,201,167,0.15);
}
.step-item.done .step-circle {
    background: var(--teal-dim);
    border-color: var(--teal-dim);
    color: var(--navy);
}
.step-label {
    font-size: 0.68rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--slate);
    text-align: center;
    max-width: 80px;
}
.step-item.active .step-label { color: var(--teal); font-weight: 600; }
.step-item.done .step-label { color: var(--teal-dim); }

/* ── Cards ────────────────────────────────────────────────────── */
.card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow);
    backdrop-filter: blur(8px);
}
.card-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.25rem;
    font-weight: 400;
    color: var(--white);
    margin-bottom: 0.4rem;
    display: flex; align-items: center; gap: 0.6rem;
}
.card-subtitle {
    font-size: 0.82rem;
    color: var(--slate);
    margin-bottom: 1.4rem;
    line-height: 1.5;
}

/* ── Chat bubbles ─────────────────────────────────────────────── */
.chat-wrap { display: flex; flex-direction: column; gap: 0.9rem; }
.bubble {
    display: flex;
    gap: 0.7rem;
    align-items: flex-start;
    animation: fadeUp 0.3s ease;
}
@keyframes fadeUp {
    from { opacity:0; transform: translateY(8px); }
    to   { opacity:1; transform: translateY(0); }
}
.bubble.agent { flex-direction: row; }
.bubble.patient { flex-direction: row-reverse; }
.bubble-avatar {
    width: 34px; height: 34px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; flex-shrink: 0;
}
.bubble.agent .bubble-avatar  { background: rgba(0,201,167,0.18); }
.bubble.patient .bubble-avatar { background: rgba(245,200,66,0.18); }
.bubble-body {
    max-width: 78%;
    padding: 0.8rem 1.1rem;
    border-radius: 12px;
    font-size: 0.9rem;
    line-height: 1.55;
}
.bubble.agent .bubble-body {
    background: rgba(0, 201, 167, 0.1);
    border: 1px solid rgba(0,201,167,0.2);
    border-top-left-radius: 3px;
    color: var(--white);
}
.bubble.patient .bubble-body {
    background: rgba(245,200,66,0.12);
    border: 1px solid rgba(245,200,66,0.2);
    border-top-right-radius: 3px;
    color: var(--white);
}
.bubble-meta {
    font-size: 0.68rem;
    color: var(--slate);
    margin-top: 4px;
}
.bubble.patient .bubble-meta { text-align: right; }

/* ── Q counter badge ──────────────────────────────────────────── */
.q-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(0,201,167,0.12);
    border: 1px solid var(--teal);
    color: var(--teal);
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 1rem;
}
.q-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--teal);
    animation: pulse 1.4s infinite;
}
@keyframes pulse {
    0%,100% { opacity:1; transform: scale(1); }
    50%      { opacity:0.5; transform: scale(0.7); }
}

/* ── Progress bar custom ──────────────────────────────────────── */
.prog-wrap {
    background: var(--navy-soft);
    border-radius: 99px;
    height: 6px;
    margin: 0.6rem 0 1.2rem;
    overflow: hidden;
}
.prog-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, var(--teal), #6af0d8);
    transition: width 0.5s ease;
}

/* ── Disclaimer banner ────────────────────────────────────────── */
.disclaimer {
    background: rgba(255,107,107,0.08);
    border: 1px solid rgba(255,107,107,0.3);
    border-left: 4px solid var(--rose);
    border-radius: 8px;
    padding: 0.75rem 1.1rem;
    font-size: 0.8rem;
    color: #ffb3b3;
    margin-bottom: 1.5rem;
    line-height: 1.5;
}

/* ── Info / success boxes ─────────────────────────────────────── */
.info-box {
    background: rgba(0,201,167,0.07);
    border: 1px solid rgba(0,201,167,0.25);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    font-size: 0.88rem;
    color: #a8f0e0;
    margin: 1rem 0;
    line-height: 1.6;
}
.gold-box {
    background: rgba(245,200,66,0.07);
    border: 1px solid rgba(245,200,66,0.3);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    font-size: 0.88rem;
    color: #fde98a;
    margin: 1rem 0;
    line-height: 1.6;
}

/* ── Report block ─────────────────────────────────────────────── */
.report-block {
    background: var(--navy-mid);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2rem 2.2rem;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem;
    line-height: 1.8;
    color: #d4e4f5;
    white-space: pre-wrap;
    word-break: break-word;
}
.report-header {
    font-family: 'DM Serif Display', serif;
    font-size: 1.5rem;
    color: var(--teal);
    margin-bottom: 0.3rem;
}
.report-meta {
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--slate);
    letter-spacing: 0.05em;
    margin-bottom: 1.5rem;
}

/* ── Buttons override ─────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, var(--teal) 0%, var(--teal-dim) 100%) !important;
    color: var(--navy) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 1.4rem !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.02em !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(0,201,167,0.35) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Inputs ───────────────────────────────────────────────────── */
.stTextArea textarea, .stTextInput input {
    background: rgba(15,32,64,0.9) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--white) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 3px rgba(0,201,167,0.12) !important;
}

/* ── Selectbox ────────────────────────────────────────────────── */
.stSelectbox > div > div {
    background: rgba(15,32,64,0.9) !important;
    border-color: var(--border) !important;
    color: var(--white) !important;
}

/* ── Thread ID chip ───────────────────────────────────────────── */
.thread-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(10,22,40,0.9);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 4px 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--slate);
}
.thread-chip span { color: var(--teal); }

/* ── Hide Streamlit branding ──────────────────────────────────── */
#MainMenu, footer { visibility: hidden; }
</style>
  
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# STATE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def init_state():
    defaults = {
        "screen":            1,          # 1 | 2 | 3 | 4
        "thread_id":         None,
        "patient_alias":     "",
        "patient_info":      "",
        "question_count":    0,
        "chat_history":      [],         # list of {"role": "agent"|"patient", "text": str}
        "diagnostic_summary": "",
        "interim_care":      "",
        "physician_treatment": "",
        "final_report":      "",
        "api_error":         None,
        "loading":           False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
S = st.session_state   # short alias


# ══════════════════════════════════════════════════════════════════════════════
# API HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def api_post(path: str, payload: dict) -> dict | None:
    """POST to FastAPI backend. Returns JSON dict or sets error."""
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        S.api_error = "❌ Impossible de joindre le backend (http://localhost:8000). Lancez `uvicorn app.api:app --reload`."
        return None
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        S.api_error = f"❌ Erreur API {e.response.status_code} : {detail}"
        return None
    except Exception as e:
        S.api_error = f"❌ Erreur inattendue : {e}"
        return None


def api_get(path: str) -> dict | None:
    """GET from FastAPI backend. Returns JSON dict or sets error."""
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        S.api_error = "❌ Impossible de joindre le backend (http://localhost:8000). Lancez `uvicorn app.api:app --reload`."
        return None
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        S.api_error = f"❌ Erreur API {e.response.status_code} : {detail}"
        return None
    except Exception as e:
        S.api_error = f"❌ Erreur inattendue : {e}"
        return None


def extract_last_question(state_data: dict) -> str:
    """Extract the latest agent question from API state response."""
    messages = state_data.get("state", {}).get("messages", [])
    for msg in reversed(messages):
        msg_type = msg.get("type", "")
        content  = msg.get("content", "")
        if msg_type in ("AIMessage", "ToolMessage") and "[Question" in content:
            # Strip prefix noise
            for line in content.split("\n"):
                if "[Question" in line:
                    return line.strip()
            return content.strip()
    # Fallback: last AI message content
    for msg in reversed(messages):
        if msg.get("type") == "AIMessage" and msg.get("content", "").strip():
            return msg["content"].strip()
    return "Le système vous posera une question. Veuillez patienter…"


def sync_state_from_api(data: dict):
    """Sync local session_state from API response dict."""
    if not data:
        return
    state_inner = data.get("state", data)
    S.question_count     = data.get("question_count",    state_inner.get("question_count",    S.question_count))
    S.diagnostic_summary = state_inner.get("diagnostic_summary", S.diagnostic_summary)
    S.interim_care       = state_inner.get("interim_care",        S.interim_care)
    S.physician_treatment= state_inner.get("physician_treatment", S.physician_treatment)
    S.final_report       = data.get("final_report",      state_inner.get("final_report",      S.final_report))


# ══════════════════════════════════════════════════════════════════════════════
# SHARED UI COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def render_header():
    st.markdown("""
    <div class="app-header">
        <div class="logo">🏥</div>
        <div>
            <h1>Système d'Orientation Clinique Simulée</h1>
            <div class="subtitle">Workflow Multi-Agents · LangGraph · Exercice Académique SMA</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_disclaimer():
    st.markdown("""
    <div class="disclaimer">
        ⚠️&nbsp; <strong>Avertissement éthique :</strong>
        Ce système est un exercice académique. Il ne constitue pas un dispositif médical
        et ne fournit aucun diagnostic définitif.
        <strong>« Ce système ne remplace pas une consultation médicale. »</strong>
    </div>
    """, unsafe_allow_html=True)


def render_stepper(current: int):
    steps = [
        ("1", "Cas patient",  "🩺"),
        ("2", "Interrogatoire", "💬"),
        ("3", "Médecin",      "👨‍⚕️"),
        ("4", "Rapport",      "📋"),
    ]
    items = ""
    for i, (num, label, icon) in enumerate(steps, 1):
        cls = "active" if i == current else ("done" if i < current else "")
        circle_content = "✓" if i < current else icon
        items += f"""
        <div class="step-item {cls}">
            <div class="step-circle">{circle_content}</div>
            <div class="step-label">{label}</div>
        </div>"""
    st.markdown(f'<div class="stepper">{items}</div>', unsafe_allow_html=True)


def render_thread_chip():
    if S.thread_id:
        short = S.thread_id[:8] + "…"
        st.markdown(
            f'<div class="thread-chip">🔗 Session&nbsp;<span>{short}</span></div>',
            unsafe_allow_html=True,
        )


def render_error():
    if S.api_error:
        st.error(S.api_error)
        if st.button("✕ Fermer l'erreur"):
            S.api_error = None
            st.rerun()


def render_chat_history():
    if not S.chat_history:
        return
    bubbles_html = '<div class="chat-wrap">'
    for entry in S.chat_history:
        role   = entry["role"]    # "agent" | "patient"
        text   = entry["text"]
        avatar = "🤖" if role == "agent" else "👤"
        label  = "Agent diagnostique" if role == "agent" else (S.patient_alias or "Patient")
        bubbles_html += f"""
        <div class="bubble {role}">
            <div class="bubble-avatar">{avatar}</div>
            <div>
                <div class="bubble-body">{text}</div>
                <div class="bubble-meta">{label}</div>
            </div>
        </div>"""
    bubbles_html += "</div>"
    st.markdown(bubbles_html, unsafe_allow_html=True)


def progress_bar(value: int, total: int = 5):
    pct = int((value / total) * 100)
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:var(--slate);margin-top:0.3rem">
        <span>Progression de l'interrogatoire</span>
        <span>{value}/{total} questions</span>
    </div>
    <div class="prog-wrap"><div class="prog-fill" style="width:{pct}%"></div></div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ÉCRAN 1 — Saisie du cas patient initial
# ══════════════════════════════════════════════════════════════════════════════

def screen_1():
    render_stepper(1)
    render_disclaimer()

    st.markdown("""
    <div class="card">
        <div class="card-title">🩺 Nouveau cas patient</div>
        <div class="card-subtitle">
            Décrivez le cas clinique fictif à analyser. Le système multi-agents
            posera ensuite 5 questions structurées pour produire une
            <em>orientation clinique préliminaire</em>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        patient_alias = st.text_input(
            "Identifiant patient (anonymisé)",
            value=S.patient_alias or "Patient A",
            placeholder="ex : Patient A, Cas 01…",
            help="Alias fictif — aucune donnée réelle.",
        )

    with col2:
        scenario = st.selectbox(
            "Scénario prédéfini (optionnel)",
            ["— Saisie libre —",
             "🫁 Syndrome respiratoire simple",
             "🚨 Cas avec red flags",
             "✅ Cas bénin (fatigue légère)"],
            help="Pré-remplit la description pour les tests.",
        )

    SCENARIOS = {
        "🫁 Syndrome respiratoire simple":
            "Patient de 34 ans, toux sèche persistante depuis 4 jours, légère fièvre à 37.8°C, "
            "rhinorrhée claire. Pas d'antécédent notable. Travaille en open-space.",
        "🚨 Cas avec red flags":
            "Patient de 58 ans, douleur thoracique irradiant vers le bras gauche depuis 2h, "
            "essoufflement au moindre effort, sueurs froides. Antécédents : HTA, diabète type 2.",
        "✅ Cas bénin (fatigue légère)":
            "Étudiant de 22 ans, fatigue légère depuis 1 semaine, légère céphalée le matin. "
            "Dort 5h par nuit en période d'examens. Pas de fièvre, pas d'autre symptôme.",
    }

    prefill = SCENARIOS.get(scenario, "")

    patient_info = st.text_area(
        "Description du cas patient",
        value=prefill,
        height=160,
        placeholder=(
            "ex : Femme de 45 ans, toux sèche depuis 5 jours, fièvre à 38.2°C, "
            "léger essoufflement à l'effort, pas d'antécédent majeur…"
        ),
        help="Minimum 10 caractères. Soyez précis pour de meilleures orientations.",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    col_btn, col_info = st.columns([1, 2])

    with col_btn:
        launch = st.button("🚀 Démarrer la consultation", use_container_width=True)

    with col_info:
        st.markdown("""
        <div class="info-box">
            Le système va créer une session, puis lancer le workflow
            DiagnosticAgent → PhysicianReview → ReportAgent via LangGraph.
        </div>
        """, unsafe_allow_html=True)

    if launch:
        if len(patient_info.strip()) < 10:
            st.warning("⚠️ Veuillez saisir une description d'au moins 10 caractères.")
            return

        S.api_error = None
        S.loading = True

        with st.spinner("Création de la session…"):
            sess = api_post("/sessions/start", {
                "patient_alias": patient_alias or "Patient Anonyme",
                "metadata": {"source": "streamlit_frontend"},
            })

        if not sess:
            render_error()
            return

        # SessionStartResponse fields
        S.thread_id     = sess["thread_id"]
        S.patient_alias = sess.get("patient_alias", patient_alias)
        S.patient_info  = patient_info.strip()
        S.chat_history  = []
        S.question_count = 0

        with st.spinner("Lancement du workflow LangGraph… (peut prendre 10-30s)"):
            result = api_post("/consultation/start", {
                "thread_id":    S.thread_id,
                "patient_info": S.patient_info,
            })

        if not result:
            render_error()
            return

        sync_state_from_api(result)

        # Push first question to chat history
        first_q = extract_last_question(result)
        S.chat_history.append({"role": "agent", "text": first_q})

        S.loading = False
        S.screen  = 2
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ÉCRAN 2 — Questions / Réponses Patient
# ══════════════════════════════════════════════════════════════════════════════

def screen_2():
    render_stepper(2)

    col_title, col_chip = st.columns([4, 1])
    with col_title:
        st.markdown("""
        <div class="card-title" style="font-family:'DM Serif Display',serif;font-size:1.35rem;margin-bottom:0.3rem">
            💬 Interrogatoire patient
        </div>
        <div class="card-subtitle" style="font-size:0.83rem;color:#8da0b3">
            L'agent diagnostique pose 5 questions successives pour collecter les informations cliniques.
            Répondez en tant que patient fictif.
        </div>
        """, unsafe_allow_html=True)
    with col_chip:
        render_thread_chip()

    render_disclaimer()

    # ── Progress ────────────────────────────────────────────────────────────
    qc = S.question_count
    progress_bar(min(qc, 5))

    badge_color = "#f5c842" if qc >= 5 else "#00c9a7"
    badge_label = "✓ Interrogatoire terminé" if qc >= 5 else f"Question {qc}/5 en cours"
    st.markdown(f"""
    <div class="q-badge" style="border-color:{badge_color};color:{badge_color};background:rgba(0,0,0,0.15)">
        {'<div class="q-dot" style="background:'+badge_color+'"></div>' if qc < 5 else ""}
        {badge_label}
    </div>
    """, unsafe_allow_html=True)

    # ── Chat history ────────────────────────────────────────────────────────
    render_chat_history()

    has_summary = getattr(S, "diagnostic_summary", "") or S.diagnostic_summary
    is_awaiting = getattr(S, "status", "") == "awaiting_physician_review"

    if has_summary or is_awaiting:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="info-box">
            ✅ <strong>Interrogatoire complet.</strong> L'agent a collecté les 5 réponses
            et produit une synthèse clinique préliminaire. La revue médicale est disponible.
        </div>
        """, unsafe_allow_html=True)
        if st.button("➡️ Passer à la revue médicale", use_container_width=True):
            S.screen = 3
            st.rerun()
        return

    # ── Zone de réponse patient ─────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.8rem;color:#8da0b3;margin-bottom:4px;">👤 Votre réponse (en tant que patient fictif)</div>',
        unsafe_allow_html=True,
    )

    answer_key = f"answer_q{qc}"
    answer = st.text_area(
        label="answer_hidden",
        label_visibility="collapsed",
        key=answer_key,
        height=100,
        placeholder="Tapez votre réponse ici…",
    )

    col_send, col_skip = st.columns([3, 1])

    with col_send:
        send = st.button("📤 Envoyer la réponse", use_container_width=True)
    with col_skip:
        skip = st.button("⏭ Passer", use_container_width=True, help="Envoyer une réponse vide")

    if send or skip:
        content = answer.strip() if (send and answer.strip()) else "(Pas de réponse fournie)"

        # Add patient bubble immediately
        S.chat_history.append({"role": "patient", "text": content})

        S.api_error = None
        with st.spinner("L'agent analyse votre réponse…"):
            result = api_post("/consultation/resume", {
                "thread_id":   S.thread_id,
                "resume_type": "patient_answer",
                "content":     content,
            })

        if not result:
            S.chat_history.pop()  # rollback optimistic update
            render_error()
            return

        sync_state_from_api(result)

        status = result.get("status", "")
        new_qc = result.get("question_count", S.question_count)
        
        S.status = status
        S.diagnostic_summary = result.get("diagnostic_summary", "")

        backend_answers = result.get("patient_answers", [])
        if not backend_answers and hasattr(S, "patient_answers"):
            backend_answers = S.patient_answers

        if len(backend_answers) >= 5 or status == "awaiting_physician_review":
            summary_msg = (
                "✅ Interrogatoire complet. L'agent a collecté les 5 réponses et produit une synthèse clinique préliminaire. "
                "La revue médicale est disponible."
            )
            if {"role": "agent", "text": summary_msg} not in S.chat_history:
                S.chat_history.append({"role": "agent", "text": summary_msg})
            
            S.screen = 2  
            st.rerun()

        else:
            next_q = extract_last_question(result)
            if next_q:
                if not any(msg.get("text") == next_q for msg in S.chat_history):
                    S.chat_history.append({"role": "agent", "text": next_q})
            
            S.screen = 2
            st.rerun()

    render_error()

# ══════════════════════════════════════════════════════════════════════════════
# ÉCRAN 3 — Revue du médecin (Human-in-the-Loop)
# ══════════════════════════════════════════════════════════════════════════════

def screen_3():
    render_stepper(3)

    col_title, col_chip = st.columns([4, 1])
    with col_title:
        st.markdown("""
        <div class="card-title" style="font-family:'DM Serif Display',serif;font-size:1.35rem;margin-bottom:0.3rem">
            👨‍⚕️ Revue du médecin traitant
        </div>
        <div class="card-subtitle" style="font-size:0.83rem;color:#8da0b3">
            Étape Human-in-the-Loop. Vous jouez le rôle du médecin traitant.
            Examinez la synthèse et proposez votre traitement / conduite à tenir.
        </div>
        """, unsafe_allow_html=True)
    with col_chip:
        render_thread_chip()

    render_disclaimer()

    # ── Récupérer l'état à jour si nécessaire ──────────────────────────────
    if not S.diagnostic_summary:
        with st.spinner("Récupération de la synthèse…"):
            data = api_get(f"/consultation/{S.thread_id}")
        if data:
            S.diagnostic_summary = data.get("diagnostic_summary") or ""
            S.interim_care       = data.get("interim_care") or ""

    # ── Affichage de la synthèse clinique ──────────────────────────────────
    st.markdown("""
    <div class="card">
        <div class="card-title">📋 Synthèse clinique préliminaire</div>
        <div class="card-subtitle">
            Produite par le DiagnosticAgent à partir des 5 réponses collectées.
            <em>Il ne s'agit pas d'un diagnostic définitif.</em>
        </div>
    </div>
    """, unsafe_allow_html=True)

    summary_text = S.diagnostic_summary or "Synthèse en cours de génération…"
    st.markdown(f'<div class="info-box">{summary_text}</div>', unsafe_allow_html=True)

    if S.interim_care:
        st.markdown("""
        <div class="card-title" style="font-size:1rem;margin:1.2rem 0 0.5rem">
            💊 Recommandation intermédiaire
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f'<div class="gold-box">{S.interim_care}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Zone de saisie médecin ──────────────────────────────────────────────
    st.markdown("""
    <div class="card-title" style="font-size:1.1rem;margin-bottom:0.5rem">
        ✍️ Votre avis médical (traitement / conduite à tenir)
    </div>
    <div class="card-subtitle" style="font-size:0.82rem">
        En tant que médecin traitant, proposez votre traitement ou conduite à tenir.
        Votre saisie sera intégrée dans le rapport final.
    </div>
    """, unsafe_allow_html=True)

    TREATMENT_TEMPLATES = {
        "— Saisie libre —": "",
        "🫁 Traitement respiratoire":
            "Prescription : paracétamol 1g × 3/j si fièvre. Sirop antitussif si besoin. "
            "Repos 3 jours. Réévaluation si fièvre > 38.5°C persistante au-delà de 48h "
            "ou aggravation de la dyspnée. Pas d'antibiothérapie d'emblée (virose probable).",
        "🚨 Orientation urgences":
            "Orientation immédiate vers les urgences médicales. Appel SAMU 15 recommandé. "
            "ECG et bilan biologique en urgence. Surveillance continue. Ne pas laisser seul.",
        "✅ Conduite conservative":
            "Pas de traitement médicamenteux nécessaire. Conseils hygiéno-diététiques : "
            "sommeil suffisant (8h min), hydratation, alimentation équilibrée. "
            "Réévaluation si persistance > 10 jours ou aggravation.",
    }

    template_choice = st.selectbox(
        "Modèle de traitement (optionnel)",
        list(TREATMENT_TEMPLATES.keys()),
        help="Sélectionnez un modèle ou rédigez librement ci-dessous.",
    )

    prefill_treatment = TREATMENT_TEMPLATES.get(template_choice, "")

    physician_input = st.text_area(
        "Traitement / Conduite à tenir",
        value=prefill_treatment,
        height=160,
        placeholder=(
            "ex : Prescription d'un antihistaminique 10mg 1×/j. "
            "Repos 48h. Réévaluation si aggravation. Éviter les efforts physiques…"
        ),
    )

    st.markdown("<br>", unsafe_allow_html=True)

    col_btn, col_note = st.columns([1, 2])

    with col_btn:
        validate = st.button("✅ Valider et générer le rapport", use_container_width=True)

    with col_note:
        st.markdown("""
        <div class="info-box" style="margin:0">
            Après validation, le <strong>ReportAgent</strong> générera le rapport final
            incluant toutes les informations et le disclaimer éthique obligatoire.
        </div>
        """, unsafe_allow_html=True)

    if validate:
        if len(physician_input.strip()) < 5:
            st.warning("⚠️ Veuillez saisir un traitement ou une conduite à tenir (min. 5 caractères).")
            return

        S.api_error = None

        with st.spinner("Transmission au ReportAgent… Génération du rapport final…"):
            result = api_post("/consultation/resume", {
                "thread_id":   S.thread_id,
                "resume_type": "physician_review",
                "content":     physician_input.strip(),
            })

        if not result:
            render_error()
            return

        S.physician_treatment = physician_input.strip()
        sync_state_from_api(result)

        # Fetch report if not already in result
        if not S.final_report:
            with st.spinner("Récupération du rapport…"):
                report_data = api_get(f"/consultation/{S.thread_id}/report")
            if report_data:
                S.final_report = report_data.get("final_report", "")

        S.screen = 4
        st.rerun()

    render_error()


# ══════════════════════════════════════════════════════════════════════════════
# ÉCRAN 4 — Rapport final
# ══════════════════════════════════════════════════════════════════════════════

def screen_4():
    render_stepper(4)

    col_title, col_chip = st.columns([4, 1])
    with col_title:
        st.markdown("""
        <div class="card-title" style="font-family:'DM Serif Display',serif;font-size:1.35rem;margin-bottom:0.3rem">
            📋 Rapport final d'orientation clinique
        </div>
        <div class="card-subtitle" style="font-size:0.83rem;color:#8da0b3">
            Généré par le ReportAgent · Workflow LangGraph complété ✓
        </div>
        """, unsafe_allow_html=True)
    with col_chip:
        render_thread_chip()

    render_disclaimer()

    # ── Fetch report if needed ──────────────────────────────────────────────
    if not S.final_report and S.thread_id:
        with st.spinner("Récupération du rapport depuis l'API…"):
            data = api_get(f"/consultation/{S.thread_id}/report")
        if data:
            S.final_report = data.get("final_report", "")
        else:
            render_error()
            return

    # ── Success banner ──────────────────────────────────────────────────────
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(0,201,167,0.12) 0%, rgba(0,168,138,0.08) 100%);
        border: 1px solid rgba(0,201,167,0.35);
        border-radius: 12px;
        padding: 1rem 1.4rem;
        margin-bottom: 1.5rem;
        display: flex; align-items: center; gap: 0.8rem;
    ">
        <span style="font-size:1.8rem">✅</span>
        <div>
            <div style="font-weight:600;color:#00c9a7;font-size:0.95rem">Workflow complété avec succès</div>
            <div style="font-size:0.8rem;color:#8da0b3;margin-top:2px">
                START → Supervisor → DiagnosticAgent × 5 → PhysicianReview → ReportAgent → END
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Report display ──────────────────────────────────────────────────────
    st.markdown("""
    <div class="report-header">Rapport d'Orientation Clinique Préliminaire</div>
    <div class="report-meta">Système Multi-Agents · LangGraph · Exercice Académique SMA</div>
    """, unsafe_allow_html=True)

    report_text = S.final_report or "Rapport non disponible."
    st.markdown(f'<div class="report-block">{report_text}</div>', unsafe_allow_html=True)

    # ── Mandatory disclaimer ────────────────────────────────────────────────
    st.markdown("""
    <div style="
        background: rgba(255,107,107,0.1);
        border: 1px solid rgba(255,107,107,0.4);
        border-radius: 10px;
        padding: 1rem 1.4rem;
        margin-top: 1.5rem;
        text-align: center;
    ">
        <div style="font-size:1.2rem;margin-bottom:4px">⚕️</div>
        <div style="font-size:0.9rem;font-weight:600;color:#ffb3b3">
            « Ce système ne remplace pas une consultation médicale. »
        </div>
        <div style="font-size:0.75rem;color:#8da0b3;margin-top:4px">
            Ce rapport est produit dans le cadre d'un exercice académique (Module SMA).
            Pour toute question médicale réelle, consultez un professionnel de santé qualifié.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Actions ─────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📥 Télécharger le rapport (.txt)", use_container_width=True):
            st.download_button(
                label="⬇️ Confirmer le téléchargement",
                data=report_text.encode("utf-8"),
                file_name=f"rapport_clinique_{S.thread_id[:8]}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with col2:
        if st.button("🔁 Nouvelle consultation", use_container_width=True):
            # Reset all state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    with col3:
        if st.button("📊 Voir l'état du workflow", use_container_width=True):
            if S.thread_id:
                state_data = api_get(f"/consultation/{S.thread_id}")
                if state_data:
                    with st.expander("🔍 État LangGraph complet", expanded=True):
                        st.json(state_data)

    render_error()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Debug / Info
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("### 🔧 Panneau de debug")
        st.markdown(f"**Écran actuel :** {S.screen}/4")
        st.markdown(f"**Thread ID :** `{S.thread_id or '—'}`")
        st.markdown(f"**Questions posées :** {S.question_count}/5")
        st.markdown(f"**Synthèse :** {'✓' if S.diagnostic_summary else '✗'}")
        st.markdown(f"**Médecin :** {'✓' if S.physician_treatment else '✗'}")
        st.markdown(f"**Rapport :** {'✓' if S.final_report else '✗'}")

        st.markdown("---")
        st.markdown("**🔗 Liens utiles**")
        st.markdown("• [API Docs](http://localhost:8000/docs)")
        st.markdown("• [Health check](http://localhost:8000/health)")

        if S.thread_id:
            st.markdown("---")
            if st.button("🔄 Forcer la synchro API"):
                data = api_get(f"/consultation/{S.thread_id}")
                if data:
                    S.diagnostic_summary = data.get("diagnostic_summary") or S.diagnostic_summary
                    S.interim_care       = data.get("interim_care") or S.interim_care
                    S.physician_treatment= data.get("physician_treatment") or S.physician_treatment
                    S.question_count     = data.get("question_count", S.question_count)
                    st.success("Synchronisé !")
                    st.rerun()

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.7rem;color:#8da0b3;line-height:1.6">
            ⚠️ Exercice académique<br>
            Module : Système Multi-Agents<br>
            Technologies : LangGraph · LangChain<br>
            FastAPI · MCP · Streamlit
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════

render_header()
render_sidebar()

# Navigation manuelle (en cas de besoin)
nav_cols = st.columns(4)
nav_labels = ["1 · Cas patient", "2 · Interrogatoire", "3 · Médecin", "4 · Rapport"]
for i, (col, label) in enumerate(zip(nav_cols, nav_labels), 1):
    with col:
        if S.screen == i:
            st.markdown(
                f'<div style="text-align:center;font-size:0.75rem;color:#00c9a7;font-weight:600;padding:4px 0;border-bottom:2px solid #00c9a7">{label}</div>',
                unsafe_allow_html=True,
            )
        else:
            if st.button(label, key=f"nav_{i}", use_container_width=True):
                S.screen = i
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Route to the correct screen
screens = {1: screen_1, 2: screen_2, 3: screen_3, 4: screen_4}
screens.get(S.screen, screen_1)()