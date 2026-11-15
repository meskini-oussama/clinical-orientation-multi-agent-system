"""
care_tools.py - Outils de recommandation de soins intermédiaires

Ce module définit le tool `recommend_interim_care` utilisé par le DiagnosticAgent
pour proposer des recommandations générales prudentes et non médicales.

⚠️  Rappel éthique important :
    Les recommandations produites par ce tool sont GÉNÉRALES et PRUDENTES.
    Elles ne constituent PAS un diagnostic médical ni une prescription.
    « Ce système ne remplace pas une consultation médicale. »
"""

from langchain_core.tools import tool


# ── Recommandations par catégorie de symptômes ──────────────────────────────────
GENERAL_RECOMMENDATIONS = {
    "default": [
        "🛌 Repos suffisant : évitez les activités physiques intenses.",
        "💧 Hydratation : buvez régulièrement de l'eau (1,5 à 2 litres par jour).",
        "🌡️  Surveillance : notez l'évolution de vos symptômes.",
        "⚠️  Consultation rapide : si aggravation, consultez un médecin sans délai.",
        "💊 Ne prenez aucun médicament sans avis médical préalable.",
    ],
    "respiratoire": [
        "🛌 Repos complet et évitez les efforts respiratoires.",
        "💧 Hydratation importante pour fluidifier les sécrétions.",
        "🌬️  Aérez légèrement la pièce sans courant d'air froid.",
        "🌡️  Surveillance de la température (consultez si > 38,5°C).",
        "🚨 Red flag : difficultés respiratoires sévères → urgences médicales immédiates.",
    ],
    "digestif": [
        "🍵 Alimentation légère : bouillons, riz, pain grillé.",
        "💧 Hydratation essentielle pour compenser les pertes éventuelles.",
        "🛌 Repos en position confortable.",
        "⏰ Observation : si symptômes > 48h, consultez un médecin.",
        "🚨 Red flag : sang dans les selles ou vomissements → urgences médicales.",
    ],
    "douleur": [
        "🛌 Repos dans une position antalgique (qui soulage la douleur).",
        "❄️  Application locale de chaud ou froid selon le type de douleur.",
        "📵 Évitez les activités aggravantes.",
        "⏰ Si douleur persistante ou intense, consultez rapidement.",
        "🚨 Red flag : douleur thoracique irradiant au bras → urgences médicales.",
    ],
}


@tool
def recommend_interim_care(symptom_category: str = "default") -> str:
    """
    Génère une recommandation intermédiaire générale et prudente pour le patient.

    Ce tool produit des conseils de soins préliminaires basés sur la catégorie
    de symptômes identifiée. Ces recommandations sont GÉNÉRALES et ne remplacent
    en aucun cas l'avis d'un médecin.

    Paramètres :
    ------------
    symptom_category : str
        Catégorie de symptômes identifiée par l'agent.
        Valeurs acceptées : "default", "respiratoire", "digestif", "douleur".
        Si la catégorie n'est pas reconnue, les recommandations générales sont utilisées.

    Retourne :
    ----------
    str
        Recommandation intermédiaire structurée avec disclaimer éthique obligatoire.

    Exemple :
    ---------
    >>> care = recommend_interim_care.invoke({"symptom_category": "respiratoire"})
    >>> print(care)
    "=== RECOMMANDATION INTERMÉDIAIRE (orientation clinique préliminaire) ===..."
    """
    # Normalisation de la catégorie
    category = symptom_category.lower().strip()
    if category not in GENERAL_RECOMMENDATIONS:
        category = "default"

    recommendations = GENERAL_RECOMMENDATIONS[category]
    recommendations_text = "\n".join(recommendations)

    # Construction du message de recommandation avec disclaimer obligatoire
    output = f"""
=== RECOMMANDATION INTERMÉDIAIRE (orientation clinique préliminaire) ===

⚠️  IMPORTANT : Ces recommandations sont générales et prudentes.
    Elles constituent une orientation préliminaire et NON un diagnostic médical.

Conseils immédiats pour votre confort :
{recommendations_text}

─────────────────────────────────────────────────────────────────────
🏥 Signes nécessitant une consultation URGENTE :
   • Difficultés respiratoires sévères
   • Douleur thoracique intense
   • Perte de conscience ou confusion
   • Saignements importants inexpliqués
   • Fièvre très élevée (> 39,5°C) résistante
─────────────────────────────────────────────────────────────────────

⚕️  « Ce système ne remplace pas une consultation médicale. »
    Un médecin traitant examinera votre situation et proposera
    un traitement adapté à votre cas spécifique.
""".strip()

    return output


@tool
def get_red_flags_check(symptoms_description: str) -> str:
    """
    Vérifie la présence de signes d'alarme (red flags) dans la description
    des symptômes du patient et retourne une alerte si nécessaire.

    Ce tool est utilisé par le DiagnosticAgent pour identifier rapidement
    les situations nécessitant une attention médicale urgente.

    Paramètres :
    ------------
    symptoms_description : str
        Description des symptômes du patient telle que recueillie
        lors de l'interrogatoire.

    Retourne :
    ----------
    str
        Rapport sur la présence ou l'absence de red flags.
    """
    RED_FLAGS_KEYWORDS = [
        "difficultés à respirer", "douleur thoracique", "perte de conscience",
        "saignement", "paralysie", "confusion", "fièvre très élevée",
        "vomissements de sang", "dyspnée sévère", "syncope",
    ]

    symptoms_lower = symptoms_description.lower()
    detected_flags = [
        flag for flag in RED_FLAGS_KEYWORDS
        if flag in symptoms_lower
    ]

    if detected_flags:
        flags_list = "\n   • ".join(detected_flags)
        return (
            f"🚨 ALERTE RED FLAGS DÉTECTÉS :\n"
            f"   • {flags_list}\n\n"
            f"⚠️  Ces signes peuvent nécessiter une consultation médicale URGENTE.\n"
            f"    Veuillez orienter le patient vers une structure de soins immédiatement.\n\n"
            f"⚕️  « Ce système ne remplace pas une consultation médicale. »"
        )
    else:
        return (
            "✅ Aucun signe d'alarme majeur (red flag) détecté dans la description.\n"
            "   Le workflow suit son cours normal vers la synthèse clinique préliminaire.\n\n"
            "⚕️  « Ce système ne remplace pas une consultation médicale. »"
        )