"""
backend/app/api.py - API FastAPI du système d'orientation clinique simulée

Endpoints obligatoires :
────────────────────────
    POST   /sessions/start               → Créer une nouvelle session
    POST   /consultation/start           → Démarrer une consultation complète
    POST   /consultation/resume          → Reprendre après interruption (médecin ou patient)
    GET    /consultation/{thread_id}     → État actuel de la consultation
    GET    /consultation/{thread_id}/report → Rapport final

⚠️  AVERTISSEMENT ÉTHIQUE :
    Ce système est un exercice académique.
    Il ne constitue pas un dispositif médical.
    Il ne fournit aucun diagnostic définitif.
    « Ce système ne remplace pas une consultation médicale. »

Lancement :
    cd backend
    uvicorn app.api:app --reload --port 8000
"""

import uuid
from datetime import datetime
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .graph import (
    medical_graph,
    run_consultation,
    submit_patient_answer,
    resume_with_physician_treatment,
    get_consultation_state,
)


# ══════════════════════════════════════════════════════════════════════════════
# INITIALISATION FASTAPI
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Système d'Orientation Clinique Simulée",
    description=(
        "API académique pour le workflow multi-agents d'orientation clinique simulée. "
        "⚠️ Ce système est un exercice académique. "
        "Il ne constitue pas un dispositif médical. "
        "« Ce système ne remplace pas une consultation médicale. »"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS pour le frontend Streamlit ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production : restreindre aux origines connues
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Stockage en mémoire des sessions actives ─────────────────────────────────
# En production, utiliser Redis ou une base de données persistante
active_sessions: dict[str, dict] = {}


# ══════════════════════════════════════════════════════════════════════════════
# SCHÉMAS PYDANTIC
# ══════════════════════════════════════════════════════════════════════════════

class SessionStartRequest(BaseModel):
    """Requête pour démarrer une session."""
    patient_alias: str = Field(
        default="Patient Anonyme",
        description="Alias ou identifiant anonymisé du patient fictif.",
        example="Patient A",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Métadonnées optionnelles (contexte académique, etc.)",
    )


class SessionStartResponse(BaseModel):
    """Réponse à la création d'une session."""
    thread_id: str
    patient_alias: str
    created_at: str
    status: str
    message: str
    ethical_notice: str = "⚠️ Ce système ne remplace pas une consultation médicale."


class ConsultationStartRequest(BaseModel):
    """Requête pour démarrer une consultation."""
    thread_id: str = Field(
        description="Identifiant de session créé via POST /sessions/start",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    patient_info: str = Field(
        description="Description initiale du cas patient fictif.",
        example="Patient de 35 ans présentant une toux sèche depuis 3 jours avec légère fièvre.",
        min_length=10,
    )


class ConsultationResumeRequest(BaseModel):
    """
    Requête pour reprendre le workflow après une interruption.

    Utilisée pour deux cas :
        1. Réponse du patient à une question du DiagnosticAgent.
        2. Validation du médecin traitant (Human-in-the-Loop).
    """
    thread_id: str = Field(
        description="Identifiant de la session à reprendre.",
    )
    resume_type: str = Field(
        description="Type de reprise : 'patient_answer' ou 'physician_review'",
        example="physician_review",
    )
    content: str = Field(
        description=(
            "Contenu de la reprise :\n"
            "  - Pour 'patient_answer' : réponse du patient à la question posée.\n"
            "  - Pour 'physician_review' : traitement / conduite à tenir du médecin."
        ),
        example="Prescription d'un antihistaminique et repos 48h. Réévaluation si fièvre > 38.5°C.",
        min_length=1,
    )


class ConsultationStateResponse(BaseModel):
    """Réponse contenant l'état actuel de la consultation."""
    thread_id: str
    status: str
    question_count: int
    current_step: str
    diagnostic_summary: Optional[str]
    interim_care: Optional[str]
    physician_treatment: Optional[str]
    has_final_report: bool
    messages_count: int
    ethical_notice: str = "⚠️ Ce système ne remplace pas une consultation médicale."


class ReportResponse(BaseModel):
    """Réponse contenant le rapport final de consultation."""
    thread_id: str
    final_report: str
    generated_at: str
    ethical_disclaimer: str = "« Ce système ne remplace pas une consultation médicale. »"
    status: str = "completed"


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée."""
    error: str
    detail: str
    thread_id: Optional[str] = None
    ethical_notice: str = "⚠️ Ce système ne remplace pas une consultation médicale."


# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def _serialize_state(state: dict) -> dict:
    """Sérialise l'état LangGraph en dictionnaire JSON-safe."""
    messages = state.get("messages", [])
    serialized_messages = []
    for msg in messages:
        try:
            serialized_messages.append({
                "type": msg.__class__.__name__,
                "content": msg.content if hasattr(msg, "content") else str(msg),
                "name": getattr(msg, "name", None),
            })
        except Exception:
            serialized_messages.append({"type": "unknown", "content": str(msg)})

    return {
        "question_count":     state.get("question_count", 0),
        "current_question":   state.get("current_question", ""),
        "awaiting_patient":   state.get("awaiting_patient", False),
        "patient_answers":    state.get("patient_answers") or [],
        "diagnostic_summary": state.get("diagnostic_summary", ""),
        "interim_care":       state.get("interim_care", ""),
        "physician_treatment":state.get("physician_treatment", ""),
        "final_report":       state.get("final_report", ""),
        "patient_info":       state.get("patient_info", ""),
        "next":               state.get("next", "diagnostic_agent"),
        "messages":           serialized_messages,
        "messages_count":     len(messages),
    }


def _determine_status(state: dict) -> str:
    """Détermine le statut actuel du workflow."""
    if state.get("final_report"):
        return "completed"
    elif state.get("physician_treatment"):
        return "generating_report"
    elif state.get("diagnostic_summary"):
        return "awaiting_physician_review"
    elif state.get("question_count", 0) > 0:
        return "questioning_patient"
    else:
        return "initializing"


def _determine_current_step(state: dict) -> str:
    """Détermine l'étape actuelle lisible."""
    status = _determine_status(state)
    steps = {
        "initializing": "Initialisation de la consultation",
        "questioning_patient": f"Question {state.get('question_count', 0)}/5 en cours",
        "awaiting_physician_review": "⏸️ En attente de la validation du médecin traitant",
        "generating_report": "Génération du rapport final",
        "completed": "✅ Consultation terminée - Rapport disponible",
    }
    return steps.get(status, "Étape inconnue")


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 0 : Racine
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Info"])
async def root():
    """Point d'entrée de l'API."""
    return {
        "name": "Système d'Orientation Clinique Simulée",
        "version": "1.0.0",
        "status": "running",
        "ethical_notice": "⚠️ Exercice académique. Ce système ne remplace pas une consultation médicale.",
        "docs": "/docs",
        "endpoints": {
            "POST /sessions/start": "Créer une nouvelle session",
            "POST /consultation/start": "Démarrer une consultation",
            "POST /consultation/resume": "Reprendre après interruption",
            "GET /consultation/{thread_id}": "État de la consultation",
            "GET /consultation/{thread_id}/report": "Rapport final",
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1 : POST /sessions/start
# ══════════════════════════════════════════════════════════════════════════════

@app.post(
    "/sessions/start",
    response_model=SessionStartResponse,
    tags=["Sessions"],
    summary="Créer une nouvelle session de consultation",
    description="Génère un thread_id unique pour une nouvelle consultation. "
                "Ce thread_id doit être utilisé pour tous les appels suivants.",
)
async def start_session(request: SessionStartRequest) -> SessionStartResponse:
    """
    Initialise une nouvelle session de consultation.

    Génère un identifiant unique (thread_id / UUID) qui sera utilisé
    comme clé de session pour toute la durée du workflow LangGraph.

    Returns:
        SessionStartResponse avec le thread_id à conserver côté client.
    """
    thread_id = str(uuid.uuid4())

    # Enregistrement de la session
    active_sessions[thread_id] = {
        "thread_id": thread_id,
        "patient_alias": request.patient_alias,
        "created_at": datetime.now().isoformat(),
        "status": "created",
        "metadata": request.metadata or {},
    }

    return SessionStartResponse(
        thread_id=thread_id,
        patient_alias=request.patient_alias,
        created_at=active_sessions[thread_id]["created_at"],
        status="created",
        message=f"Session créée. Utilisez thread_id='{thread_id}' pour démarrer la consultation.",
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2 : POST /consultation/start
# ══════════════════════════════════════════════════════════════════════════════

@app.post(
    "/consultation/start",
    tags=["Consultation"],
    summary="Démarrer le workflow de consultation clinique",
    description=(
        "Lance le graphe LangGraph avec le cas patient initial. "
        "Le workflow s'exécute jusqu'à la première interruption "
        "(avant l'étape physician_review). "
        "⚠️ Exercice académique. Ce système ne remplace pas une consultation médicale."
    ),
)
async def start_consultation(request: ConsultationStartRequest) -> dict:
    """
    Lance la consultation clinique simulée.

    Le workflow :
        START → Supervisor → DiagnosticAgent (×5 questions) → [PAUSE]
        L'exécution s'interrompt avant physician_review.
        Reprendre via POST /consultation/resume avec resume_type='physician_review'.

    Returns:
        État de la consultation après l'exécution initiale.
    """
    thread_id = request.thread_id

    # Vérification de la session
    if thread_id not in active_sessions:
        # Création automatique de session si inexistante (compatibilité)
        active_sessions[thread_id] = {
            "thread_id": thread_id,
            "patient_alias": "Patient Anonyme",
            "created_at": datetime.now().isoformat(),
            "status": "auto_created",
        }

    try:
        # Lancement du graphe LangGraph
        result_state = run_consultation(
            patient_info=request.patient_info,
            thread_id=thread_id,
        )

        # Mise à jour du statut de session
        active_sessions[thread_id]["status"] = "in_progress"
        active_sessions[thread_id]["started_at"] = datetime.now().isoformat()

        serialized = _serialize_state(result_state)
        status = _determine_status(result_state)
        current_step = _determine_current_step(result_state)

        return {
            "thread_id": thread_id,
            "status": status,
            "current_step": current_step,
            "question_count": result_state.get("question_count", 0),
            "current_question": result_state.get("current_question", ""),
            "awaiting_patient": result_state.get("awaiting_patient", False),
            "state": serialized,
            "next_action": (
                "Répondez à la question posée via POST /consultation/resume "
                "avec resume_type='patient_answer'."
            ),
            "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
        }

    except Exception as e:
        active_sessions[thread_id]["status"] = "error"
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Erreur lors du démarrage de la consultation",
                "detail": str(e),
                "thread_id": thread_id,
                "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
            }
        )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3 : POST /consultation/resume
# ══════════════════════════════════════════════════════════════════════════════

@app.post(
    "/consultation/resume",
    tags=["Consultation"],
    summary="Reprendre le workflow après une interruption",
    description=(
        "Permet de reprendre le workflow LangGraph après une interruption. "
        "Utilisé pour :\n"
        "  1. Soumettre les réponses du patient aux questions (resume_type='patient_answer')\n"
        "  2. Soumettre la validation du médecin traitant (resume_type='physician_review')\n\n"
        "⚠️ Exercice académique. Ce système ne remplace pas une consultation médicale."
    ),
)
async def resume_consultation(request: ConsultationResumeRequest) -> dict:
    """
    Reprend le workflow après une interruption Human-in-the-Loop.

    Cas d'usage :
    -------------
    1. resume_type='patient_answer' :
       Le patient répond à une question du DiagnosticAgent.
       Son contenu est injecté dans l'état et le workflow continue.

    2. resume_type='physician_review' :
       Le médecin traitant soumet son traitement / conduite à tenir.
       Le workflow continue vers le ReportAgent pour générer le rapport final.

    Returns:
        État mis à jour de la consultation.
    """
    thread_id = request.thread_id
    resume_type = request.resume_type
    content = request.content

    # Validation du type de reprise
    valid_types = {"patient_answer", "physician_review"}
    if resume_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"resume_type invalide : '{resume_type}'",
                "valid_types": list(valid_types),
                "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
            }
        )

    # Vérification de l'existence de la session
    config = {"configurable": {"thread_id": thread_id}}
    try:
        current_state_snapshot = medical_graph.get_state(config)
    except Exception:
        current_state_snapshot = None

    if not current_state_snapshot or not current_state_snapshot.values:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Consultation non trouvée pour thread_id='{thread_id}'",
                "suggestion": "Démarrez d'abord une consultation via POST /consultation/start",
                "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
            }
        )

    try:
        current_state = current_state_snapshot.values

        if resume_type == "physician_review":
            # ── CAS 1 : Validation du médecin traitant ───────────────────────
            result_state = resume_with_physician_treatment(
                thread_id=thread_id,
                physician_treatment=content,
            )

            serialized = _serialize_state(result_state)
            status = _determine_status(result_state)

            return {
                "thread_id": thread_id,
                "resume_type": resume_type,
                "status": status,
                "current_step": _determine_current_step(result_state),
                "physician_treatment_recorded": content,
                "has_final_report": bool(result_state.get("final_report")),
                "state": serialized,
                "next_action": (
                    f"Rapport disponible via GET /consultation/{thread_id}/report"
                    if result_state.get("final_report")
                    else "Génération du rapport en cours."
                ),
                "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
            }

        elif resume_type == "patient_answer":
            # ── CAS 2 : Réponse du patient à une question ────────────────────
            # submit_patient_answer :
            #   1. Accumule la réponse dans patient_answers
            #   2. Reset awaiting_patient=False
            #   3. Relance le graph → diagnostic_agent pose la Q suivante
            #      (ou génère la synthèse si c\'était la 5ème réponse)
            #   4. S\'interrompt à nouveau avant le prochain diagnostic_agent
            result_state = submit_patient_answer(
                thread_id=thread_id,
                answer=content,
            )
            serialized = _serialize_state(result_state)
            status = _determine_status(result_state)
            next_question = result_state.get("current_question", "")

            return {
                "thread_id": thread_id,
                "resume_type": resume_type,
                "status": status,
                "current_step": _determine_current_step(result_state),
                "question_count": result_state.get("question_count", 0),
                "current_question": next_question,
                "awaiting_patient": result_state.get("awaiting_patient", False),
                "patient_answer_recorded": content,
                "state": serialized,
             "next_action": (
            "Appelez POST /consultation/resume avec resume_type='physician_review'."
            if status == "awaiting_physician_review"
            else f"Question {result_state.get('question_count', 0)}/5 posée. Continuez avec la prochaine réponse."
        ),
                "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Erreur lors de la reprise de la consultation",
                "detail": str(e),
                "thread_id": thread_id,
                "resume_type": resume_type,
                "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
            }
        )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4 : GET /consultation/{thread_id}
# ══════════════════════════════════════════════════════════════════════════════

@app.get(
    "/consultation/{thread_id}",
    response_model=ConsultationStateResponse,
    tags=["Consultation"],
    summary="Obtenir l'état actuel d'une consultation",
    description="Retourne l'état complet de la consultation identifiée par thread_id.",
)
async def get_consultation(thread_id: str) -> ConsultationStateResponse:
    """
    Récupère l'état actuel d'une consultation en cours ou terminée.

    Returns:
        ConsultationStateResponse avec tous les champs de l'état.
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state_snapshot = medical_graph.get_state(config)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de l'état : {e}"
        )

    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Consultation non trouvée pour thread_id='{thread_id}'",
                "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
            }
        )

    state = state_snapshot.values
    serialized = _serialize_state(state)
    status = _determine_status(state)

    return ConsultationStateResponse(
        thread_id=thread_id,
        status=status,
        question_count=serialized["question_count"],
        current_step=_determine_current_step(state),
        diagnostic_summary=serialized["diagnostic_summary"] or None,
        interim_care=serialized["interim_care"] or None,
        physician_treatment=serialized["physician_treatment"] or None,
        has_final_report=bool(serialized["final_report"]),
        messages_count=serialized["messages_count"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 5 : GET /consultation/{thread_id}/report
# ══════════════════════════════════════════════════════════════════════════════

@app.get(
    "/consultation/{thread_id}/report",
    response_model=ReportResponse,
    tags=["Consultation"],
    summary="Obtenir le rapport final de consultation",
    description=(
        "Retourne le rapport final structuré de la consultation. "
        "Disponible uniquement si la consultation est complétée. "
        "Le rapport contient obligatoirement le disclaimer éthique : "
        "« Ce système ne remplace pas une consultation médicale. »"
    ),
)
async def get_consultation_report(thread_id: str) -> ReportResponse:
    """
    Récupère le rapport final structuré d'une consultation terminée.

    Le rapport inclut obligatoirement :
        - Synthèse clinique préliminaire
        - Recommandation intermédiaire
        - Avis du médecin traitant
        - Disclaimer éthique : « Ce système ne remplace pas une consultation médicale. »

    Returns:
        ReportResponse avec le rapport complet.
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state_snapshot = medical_graph.get_state(config)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération du rapport : {e}"
        )

    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Consultation non trouvée pour thread_id='{thread_id}'",
                "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
            }
        )

    state = state_snapshot.values
    final_report = state.get("final_report", "")

    if not final_report:
        status = _determine_status(state)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Rapport non encore disponible",
                "current_status": status,
                "current_step": _determine_current_step(state),
                "suggestion": (
                    "Le rapport sera disponible après la validation du médecin traitant. "
                    "Utilisez POST /consultation/resume avec resume_type='physician_review'."
                ),
                "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
            }
        )

    return ReportResponse(
        thread_id=thread_id,
        final_report=final_report,
        generated_at=datetime.now().isoformat(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS BONUS : Sessions et Health
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/sessions", tags=["Sessions"], summary="Lister les sessions actives")
async def list_sessions() -> dict:
    """Retourne la liste des sessions actives (usage académique/debug)."""
    return {
        "active_sessions_count": len(active_sessions),
        "sessions": list(active_sessions.values()),
        "ethical_notice": "⚠️ Ce système ne remplace pas une consultation médicale.",
    }


@app.get("/health", tags=["Info"], summary="Health check")
async def health_check() -> dict:
    """Vérification de santé de l'API."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "graph_loaded": medical_graph is not None,
        "ethical_notice": "⚠️ Exercice académique. Ce système ne remplace pas une consultation médicale.",
    }