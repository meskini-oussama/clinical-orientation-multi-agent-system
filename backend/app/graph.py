'PYEOF'
"""
graph.py - Orchestration du workflow multi-agents médical (v2 — interactive)

Architecture des interruptions :
──────────────────────────────────────────────────────────────────────
  START → supervisor → diagnostic_agent
                            │
                    interrupt_before=["diagnostic_agent"]
                    (déclenché à chaque question)
                            │
          [frontend envoie la réponse via /consultation/resume]
                            │
             (répété 5 fois, puis synthèse automatique)
                            │
          supervisor → physician_review
                            │
                    interrupt_before=["physician_review"]
                    (médecin saisit son traitement)
                            │
          supervisor → report_agent → supervisor → END

Principe clé :
  • interrupt_before=["diagnostic_agent", "physician_review"]
  • À chaque réveil du diagnostic_agent, il vérifie si une réponse
    patient vient d'être injectée dans `patient_answers`.
    - S'il n'y a PAS de nouvelle réponse (premier appel) → pose la
      question N et met awaiting_patient=True, puis retourne au supervisor.
    - Le graphe s'interrompt AVANT le prochain appel à diagnostic_agent.
    - Quand le frontend reprend avec la réponse, le nœud reçoit la
      réponse, incrémente question_count, pose la suivante, etc.
  • Après 5 réponses, il génère la synthèse et passe à physician_review.

⚠️  Ce système est un exercice académique.
    « Ce système ne remplace pas une consultation médicale. »
"""

import os
from datetime import datetime
from typing import Literal

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.state import MedicalState
from app.tools.patient_tools import PATIENT_QUESTIONS
from app.tools.care_tools import GENERAL_RECOMMENDATIONS


# ══════════════════════════════════════════════════════════════════════════════
# LLM
# ══════════════════════════════════════════════════════════════════════════════

def get_llm():
    """
    Retourne le LLM configuré via variable d'environnement.

    Supporte Groq, OpenAI, Anthropic.
    Définissez dans votre .env :
        LLM_PROVIDER=groq          (groq | openai | anthropic)
        GROQ_API_KEY=gsk_...
        OPENAI_API_KEY=sk-...
        ANTHROPIC_API_KEY=sk-ant-...
    """
   
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            temperature=0,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    else:  # openai fallback
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE"),
        )


# ══════════════════════════════════════════════════════════════════════════════
# NŒUD 1 : SUPERVISOR
# ══════════════════════════════════════════════════════════════════════════════

def supervisor_node(state: MedicalState) -> MedicalState:
    """
    Orchestre le workflow. Décide du prochain nœud selon l'état.

    Règles de routage :
      1. diagnostic_summary vide  → diagnostic_agent
      2. physician_treatment vide → physician_review
      3. final_report vide        → report_agent
      4. sinon                    → FINISH
    """
    diagnostic_summary  = state.get("diagnostic_summary", "")
    physician_treatment = state.get("physician_treatment", "")
    final_report        = state.get("final_report", "")
    question_count      = state.get("question_count", 0)

    if final_report:
        next_node = "FINISH"
    elif physician_treatment:
        next_node = "report_agent"
    elif diagnostic_summary:
        next_node = "physician_review"
    else:
        next_node = "diagnostic_agent"

    log = AIMessage(
        content=(
            f"[Supervisor] → {next_node} "
            f"| Q={question_count}/5 "
            f"| synthèse={'✓' if diagnostic_summary else '✗'} "
            f"| médecin={'✓' if physician_treatment else '✗'} "
            f"| rapport={'✓' if final_report else '✗'}"
        ),
        name="supervisor",
    )
    return {**state, "next": next_node, "messages": [log]}


def supervisor_router(state: MedicalState) -> Literal[
    "diagnostic_agent", "physician_review", "report_agent", "__end__"
]:
    nxt = state.get("next", "diagnostic_agent")
    return "__end__" if nxt == "FINISH" else nxt


# ══════════════════════════════════════════════════════════════════════════════
# NŒUD 2 : DIAGNOSTIC AGENT
# ══════════════════════════════════════════════════════════════════════════════
#
# Principe d'exécution interactive (une question par invocation) :
#
#  Invocation N (question_count = N-1, awaiting_patient = False) :
#    → Pose la question N
#    → question_count++, awaiting_patient = True
#    → Retourne au supervisor qui re-route vers diagnostic_agent
#    → INTERRUPT déclenché par LangGraph avant le prochain nœud
#
#  Invocation suivante (après reprise avec réponse patient) :
#    → awaiting_patient = False (reset par l'API lors de la reprise)
#    → La réponse patient est déjà dans patient_answers
#    → Pose la question N+1, ou génère la synthèse si N == 5
#
# ══════════════════════════════════════════════════════════════════════════════

def diagnostic_agent_node(state: MedicalState) -> MedicalState:
    """
    Pose UNE question par invocation, basée STRICTEMENT sur le nombre de réponses 
    réelles stockées dans 'patient_answers'.
    """
    patient_answers = list(state.get("patient_answers") or [])
    patient_info    = state.get("patient_info", "Non renseigné.")

    # 1. Si on a déjà récolté les 5 réponses, on génère directement la synthèse
    if len(patient_answers) >= 5:
        return _generate_diagnostic_summary(state, patient_answers, patient_info)

    # 2. L'index de la question correspond exactement au nombre de réponses qu'on a déjà
    question_index = len(patient_answers)

    if question_index >= len(PATIENT_QUESTIONS):
        return _generate_diagnostic_summary(state, patient_answers, patient_info)

    question_text = PATIENT_QUESTIONS[question_index]
    display_question = f"[Question {question_index + 1}/5] {question_text}"

    question_msg = AIMessage(
        content=display_question,
        name="diagnostic_agent",
    )

    return {
        **state,
        "question_count":   question_index + 1,   # Aligné sur la question affichée
        "current_question": display_question,
        "awaiting_patient": True,                  # On attend le patient
        "messages":         [question_msg],
    }


def _generate_diagnostic_summary(
    state: MedicalState,
    patient_answers: list,
    patient_info: str,
) -> MedicalState:
    """
    Appelle le LLM pour générer la synthèse clinique préliminaire
    et la recommandation intermédiaire à partir des 5 réponses.
    """
    llm = get_llm()

    # Reconstruction de l'échange pour contexte LLM
    qa_pairs = ""
    for i, (q, a) in enumerate(zip(PATIENT_QUESTIONS, patient_answers), 1):
        qa_pairs += f"\nQ{i} : {q}\nRéponse : {a}\n"

    # Détection basique de catégorie pour la recommandation
    all_text = " ".join(patient_answers).lower()
    if any(w in all_text for w in ["toux", "respir", "gorge", "nez", "grippe"]):
        category = "respiratoire"
    elif any(w in all_text for w in ["ventre", "nausée", "vomis", "diarrhée", "digestif"]):
        category = "digestif"
    elif any(w in all_text for w in ["douleur", "mal", "douleurs"]):
        category = "douleur"
    elif any(w in all_text for w in ["tête", "vertige", "neurologique"]):
        category = "neurologique"
    else:
        category = "general"

    care_lines = GENERAL_RECOMMENDATIONS.get(category, GENERAL_RECOMMENDATIONS["default"])
    interim_care = (
        f"Catégorie identifiée : {category}\n\n"
        + "\n".join(care_lines)
        + "\n\n⚕️  « Ce système ne remplace pas une consultation médicale. »"
    )

    prompt = f"""Tu es un agent d'orientation clinique préliminaire (exercice académique).

⚠️  RÈGLE ABSOLUE : Tu NE fournis PAS de diagnostic médical définitif.
    Utilise uniquement les termes : "orientation clinique préliminaire", "synthèse clinique".

Informations initiales sur le patient :
{patient_info}

Échange complet avec le patient :
{qa_pairs}

Rédige une synthèse clinique préliminaire en français (8-12 lignes) qui :
1. Résume les symptômes rapportés par le patient
2. Identifie les éléments cliniques saillants
3. Mentionne les éventuels signes d'alarme détectés
4. Propose une orientation générale (sans diagnostic définitif)
5. Rappelle la nécessité d'une consultation médicale réelle

Commence directement par la synthèse, sans introduction."""

    response = llm.invoke([SystemMessage(content=prompt)])
    summary = response.content if isinstance(response.content, str) else str(response.content)

    # Garantie du disclaimer
    if "ne remplace pas" not in summary:
        summary += "\n\n⚕️  « Ce système ne remplace pas une consultation médicale. »"

    synthesis_msg = AIMessage(
        content=f"[DiagnosticAgent] ✅ Synthèse clinique préliminaire générée.",
        name="diagnostic_agent",
    )

    return {
        **state,
        "diagnostic_summary": summary,
        "interim_care":       interim_care,
        "awaiting_patient":   False,
        "current_question":   "",
        "messages":           [synthesis_msg],
    }


# ══════════════════════════════════════════════════════════════════════════════
# NŒUD 3 : PHYSICIAN REVIEW (Human-in-the-Loop)
# ══════════════════════════════════════════════════════════════════════════════

def physician_review_node(state: MedicalState) -> MedicalState:
    """
    Interruption Human-in-the-Loop pour le médecin traitant.
    Le graphe s'interrompt AVANT ce nœud (interrupt_before).
    Ce nœud s'exécute seulement après que le médecin a fourni son traitement.
    """
    physician_treatment = state.get("physician_treatment", "")
    diagnostic_summary  = state.get("diagnostic_summary", "")
    interim_care        = state.get("interim_care", "")

    msg = AIMessage(
        content=(
            f"[PhysicianReview ✅] Traitement du médecin enregistré.\n\n"
            f"📋 Synthèse clinique : {diagnostic_summary[:200]}…\n\n"
            f"💊 Traitement prescrit : {physician_treatment}"
        ),
        name="physician_review",
    )
    return {**state, "messages": [msg]}


# ══════════════════════════════════════════════════════════════════════════════
# NŒUD 4 : REPORT AGENT
# ══════════════════════════════════════════════════════════════════════════════

def report_agent_node(state: MedicalState) -> MedicalState:
    """Génère le rapport final structuré avec disclaimer obligatoire."""
    llm = get_llm()

    patient_info        = state.get("patient_info", "Non renseigné.")
    diagnostic_summary  = state.get("diagnostic_summary", "Non disponible.")
    interim_care        = state.get("interim_care", "Non disponible.")
    physician_treatment = state.get("physician_treatment", "Non renseigné par le médecin.")
    session_id          = state.get("session_id", "N/A")
    patient_answers     = state.get("patient_answers") or []

    qa_section = ""
    for i, (q, a) in enumerate(zip(PATIENT_QUESTIONS, patient_answers), 1):
        qa_section += f"  Q{i} : {q}\n  R{i} : {a}\n\n"

    prompt = f"""Tu es le ReportAgent d'un système académique d'orientation clinique simulée.

Génère un rapport final STRUCTURÉ en français avec exactement ces sections :

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAPPORT D'ORIENTATION CLINIQUE PRÉLIMINAIRE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Session  : {session_id}
Date     : {datetime.now().strftime("%d/%m/%Y à %H:%M")}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. CAS PATIENT INITIAL
{patient_info}

2. INTERROGATOIRE PATIENT (5 questions)
{qa_section if qa_section else "   Non disponible."}

3. SYNTHÈSE CLINIQUE PRÉLIMINAIRE
{diagnostic_summary}

4. RECOMMANDATION INTERMÉDIAIRE
{interim_care}

5. AVIS DU MÉDECIN TRAITANT
{physician_treatment}

6. CONCLUSION
[Rédige 3-4 phrases de conclusion générale sur la prise en charge recommandée]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚕️  AVERTISSEMENT ÉTHIQUE
« Ce système ne remplace pas une consultation médicale. »
Ce rapport est produit dans le cadre d'un exercice académique (Module SMA).
Il ne constitue pas un avis médical et ne doit pas être utilisé à des fins cliniques réelles.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Génère maintenant la section CONCLUSION uniquement (les autres sections sont déjà rédigées ci-dessus).
Retourne le rapport COMPLET tel qu'il est ci-dessus, en remplaçant [Rédige...] par ta conclusion."""

    response = llm.invoke([HumanMessage(content=prompt)])
    report_content = response.content if isinstance(response.content, str) else str(response.content)

    # Sécurité disclaimer
    if "ne remplace pas une consultation médicale" not in report_content:
        report_content += (
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚕️  « Ce système ne remplace pas une consultation médicale. »\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    report_msg = AIMessage(
        content="[ReportAgent] ✅ Rapport final généré.",
        name="report_agent",
    )
    return {**state, "final_report": report_content, "messages": [report_msg]}


# ══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION DU GRAPHE
# ══════════════════════════════════════════════════════════════════════════════

def build_medical_graph():
    """
    Compile le graphe LangGraph avec deux points d'interruption :
      • interrupt_before=["diagnostic_agent"]  → attend réponse patient (×5)
      • interrupt_before=["physician_review"]  → attend avis médecin (×1)
    """
    graph = StateGraph(MedicalState)

    graph.add_node("supervisor",        supervisor_node)
    graph.add_node("diagnostic_agent",  diagnostic_agent_node)
    graph.add_node("physician_review",  physician_review_node)
    graph.add_node("report_agent",      report_agent_node)

    graph.add_edge(START, "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "diagnostic_agent": "diagnostic_agent",
            "physician_review": "physician_review",
            "report_agent":     "report_agent",
            "__end__":          END,
        },
    )

    # Après chaque nœud métier → retour au supervisor
    graph.add_edge("diagnostic_agent", "supervisor")
    graph.add_edge("physician_review", "supervisor")
    graph.add_edge("report_agent",     "supervisor")

    checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["diagnostic_agent", "physician_review"],
    )


medical_graph = build_medical_graph()


# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES (utilisées par api.py)
# ══════════════════════════════════════════════════════════════════════════════

def run_consultation(patient_info: str, thread_id: str) -> dict:
    """
    Initialise proprement l'état et lance le graphe.
    """
    from app.state import get_initial_state

    initial_state = get_initial_state(patient_info=patient_info, session_id=thread_id)
    initial_state["messages"] = [HumanMessage(content=f"Cas patient : {patient_info}")]
    initial_state["question_count"] = 0
    initial_state["patient_answers"] = []

    config = {"configurable": {"thread_id": thread_id}}

    # Premier invoke pour passer START -> supervisor
    medical_graph.invoke(initial_state, config=config)
    # Deuxième invoke pour exécuter diagnostic_agent (Q1) et s'arrêter juste après
    result = medical_graph.invoke(None, config=config)
    return result


def submit_patient_answer(thread_id: str, answer: str) -> dict:
    """
    Prend la réponse du patient, l'ajoute dans le state et réveille le supervisor 
    pour recalculer proprement la suite.
    """
    config = {"configurable": {"thread_id": thread_id}}

    # 1. Récupérer les réponses actuelles
    snapshot = medical_graph.get_state(config)
    current_answers = list(snapshot.values.get("patient_answers") or [])
    current_answers.append(answer)

    patient_msg = HumanMessage(content=f"[Réponse patient] {answer}")
    
    # 2. On met à jour en disant qu'on repart du supervisor pour réévaluer les conditions
    medical_graph.update_state(
        config,
        {
            "patient_answers": current_answers,
            "awaiting_patient": False,
            "messages": [patient_msg],
        },
        as_node="supervisor", 
    )

    # 3. On relance. Le graphe va faire : supervisor -> diagnostic_agent -> INTERRUPT (pose la Q suivante)
    result = medical_graph.invoke(None, config=config)
    return result


def resume_with_physician_treatment(thread_id: str, physician_treatment: str) -> dict:
    """
    Injecte le traitement du médecin et reprend jusqu'au rapport final.
    """
    config = {"configurable": {"thread_id": thread_id}}

    medical_graph.update_state(
        config,
        {"physician_treatment": physician_treatment},
        as_node="physician_review",
    )

    result = medical_graph.invoke(None, config=config)
    return result


def get_consultation_state(thread_id: str) -> dict:
    """Récupère l'état actuel d'une consultation."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = medical_graph.get_state(config)
    return snapshot.values if snapshot else {}
