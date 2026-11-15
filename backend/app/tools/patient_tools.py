"""
patient_tools.py - Outils d'interaction avec le patient

Ce module définit le tool `ask_patient` utilisé par le DiagnosticAgent
pour poser ses 5 questions successives au patient fictif.

⚠️  Rappel éthique : ce système est un exercice académique.
    Les questions visent une orientation clinique préliminaire,
    pas un diagnostic définitif.
"""

from langchain_core.tools import tool


# ── Liste des 5 questions prédéfinies ───────────────────────────────────────────
PATIENT_QUESTIONS = [
    "Quels sont vos symptômes principaux en ce moment ? Décrivez-les le plus précisément possible.",
    "Depuis combien de temps ressentez-vous ces symptômes ? (heures, jours, semaines...)",
    "Sur une échelle de 1 à 10, quelle est l'intensité de votre gêne ou douleur ?",
    "Avez-vous des antécédents médicaux connus ou prenez-vous des médicaments actuellement ?",
    "Avez-vous de la fièvre, des difficultés à respirer, ou tout autre signe d'aggravation récente ?",
]


@tool
def ask_patient(question_count: int) -> str:
    """
    Pose une question au patient en fonction du compteur de questions actuel.

    Ce tool est appelé par le DiagnosticAgent pour recueillir des informations
    sur le patient de manière structurée. Il doit être appelé 5 fois successivement
    (question_count de 0 à 4) avant de procéder à la synthèse clinique.

    Paramètres :
    ------------
    question_count : int
        Indice de la question à poser (0 à 4).
        - 0 : symptômes principaux
        - 1 : durée des symptômes
        - 2 : intensité (échelle 1-10)
        - 3 : antécédents médicaux
        - 4 : signes d'aggravation / red flags

    Retourne :
    ----------
    str
        La question à poser au patient, ou un message indiquant que
        toutes les questions ont déjà été posées.

    Exemple d'utilisation par l'agent :
    ------------------------------------
    >>> question = ask_patient.invoke({"question_count": 0})
    >>> print(question)
    "Quels sont vos symptômes principaux en ce moment ?..."
    """
    if question_count < 0:
        return "Erreur : le compteur de questions ne peut pas être négatif."

    if question_count >= len(PATIENT_QUESTIONS):
        return (
            f"Toutes les {len(PATIENT_QUESTIONS)} questions ont été posées. "
            "Vous pouvez maintenant procéder à la synthèse clinique préliminaire."
        )

    question = PATIENT_QUESTIONS[question_count]
    remaining = len(PATIENT_QUESTIONS) - question_count - 1

    return (
        f"[Question {question_count + 1}/{len(PATIENT_QUESTIONS)}] {question}"
        + (f"\n(Il restera {remaining} question(s) après celle-ci.)" if remaining > 0 else "")
    )


@tool
def get_all_questions() -> str:
    """
    Retourne la liste complète des 5 questions que le DiagnosticAgent
    doit poser au patient. Utile pour l'initialisation ou le débogage.

    Retourne :
    ----------
    str
        Liste numérotée des 5 questions.
    """
    questions_list = "\n".join(
        [f"{i+1}. {q}" for i, q in enumerate(PATIENT_QUESTIONS)]
    )
    return f"Questions d'orientation clinique préliminaire :\n{questions_list}"