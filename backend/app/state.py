'PYEOF'
"""
state.py - État partagé du graphe médical (MedicalState)

⚠️  AVERTISSEMENT ÉTHIQUE :
    Ce système est un exercice académique. Il ne constitue pas un dispositif
    médical et ne fournit aucun diagnostic définitif.
    « Ce système ne remplace pas une consultation médicale. »
"""

from typing import Annotated, Optional
from typing_extensions import TypedDict, Literal
from langgraph.graph.message import add_messages


class MedicalState(TypedDict, total=False):
    """
    État partagé entre tous les nœuds du graphe LangGraph.

    Champs clés :
    ─────────────
    messages           : historique des messages (add_messages accumule automatiquement)
    next               : prochain nœud décidé par le Supervisor
    question_count     : nb de questions déjà POSÉES au patient (0 → 5)
    current_question   : texte de la question en attente de réponse
    awaiting_patient   : True = le graphe s'est interrompu, attend une réponse humaine
    patient_answers    : liste des réponses collectées (list[str])
    interim_care       : recommandation intermédiaire prudente
    diagnostic_summary : synthèse clinique préliminaire (≠ diagnostic définitif)
    physician_treatment: traitement du médecin (Human-in-the-Loop)
    final_report       : rapport final avec disclaimer obligatoire
    patient_info       : description initiale du cas patient
    session_id         : identifiant de session
    """

    # ── Messages ──────────────────────────────────────────────────────────────
    messages: Annotated[list, add_messages]

    # ── Orchestration ─────────────────────────────────────────────────────────
    next: Literal[
        "diagnostic_agent",
        "physician_review",
        "report_agent",
        "FINISH"
    ]

    # ── Interrogatoire patient ────────────────────────────────────────────────
    question_count: int          # Questions POSÉES jusqu'ici (0-5)
    current_question: str        # Texte de la question courante (affiché au frontend)
    awaiting_patient: bool       # True → interrompu, attend réponse patient
    patient_answers: list        # Réponses accumulées

    # ── DiagnosticAgent ───────────────────────────────────────────────────────
    interim_care: str
    diagnostic_summary: str

    # ── PhysicianReview (Human-in-the-Loop) ──────────────────────────────────
    physician_treatment: str

    # ── ReportAgent ───────────────────────────────────────────────────────────
    final_report: str

    # ── Contexte ──────────────────────────────────────────────────────────────
    patient_info: str
    session_id: str


def get_initial_state(patient_info: str = "", session_id: str = "") -> MedicalState:
    """Retourne un état initial propre pour démarrer une nouvelle consultation."""
    return MedicalState(
        messages=[],
        next="diagnostic_agent",
        question_count=0,
        current_question="",
        awaiting_patient=False,
        patient_answers=[],
        interim_care="",
        diagnostic_summary="",
        physician_treatment="",
        final_report="",
        patient_info=patient_info,
        session_id=session_id,
    )
