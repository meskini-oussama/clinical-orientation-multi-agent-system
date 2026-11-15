"""
mcp_server/server.py - Serveur MCP d'orientation clinique

Ce serveur MCP expose des outils que les agents LangGraph peuvent appeler
via le client MCP (backend/app/mcp_client.py).

Outils exposés :
────────────────
1. fetch_medical_guidelines(symptom_category)
   → Retourne des directives médicales générales par catégorie de symptômes.
   → Utilisé par le DiagnosticAgent pour enrichir son contexte.

2. log_consultation(thread_id, event_type, data)
   → Enregistre les événements de consultation dans mcp_server/data/.
   → Assure une traçabilité académique du workflow.

3. get_consultation_history(thread_id)
   → Lit et retourne l'historique d'une consultation depuis mcp_server/data/.

⚠️  AVERTISSEMENT ÉTHIQUE :
    Ce serveur est un composant d'un exercice académique.
    Les directives retournées sont générales et informatives.
    « Ce système ne remplace pas une consultation médicale. »

Lancement :
    python mcp_server/server.py
    # ou via uvicorn pour le mode HTTP (SSE)
"""

import json
import os
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ── Configuration ────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── Initialisation FastMCP ───────────────────────────────────────────────────
mcp = FastMCP(
    name="medical-orientation-mcp"
   # version="1.0.0",
    
)

# ══════════════════════════════════════════════════════════════════════════════
# BASE DE DONNÉES LOCALE DES DIRECTIVES MÉDICALES GÉNÉRALES
# (Données fictives à usage académique uniquement)
# ══════════════════════════════════════════════════════════════════════════════

MEDICAL_GUIDELINES: dict[str, dict] = {
    "respiratoire": {
        "category": "Syndrome respiratoire",
        "disclaimer": "⚠️ Orientation préliminaire uniquement. Consulter un médecin.",
        "general_info": (
            "Les symptômes respiratoires courants incluent toux, rhinorrhée, "
            "congestion nasale, et dans certains cas fièvre modérée. "
            "La majorité des infections respiratoires hautes sont d'origine virale "
            "et évoluent favorablement en 7 à 10 jours."
        ),
        "red_flags": [
            "Dyspnée sévère au repos",
            "Cyanose (lèvres ou ongles bleutés)",
            "Fréquence respiratoire > 30/min",
            "Saturation O2 < 92%",
            "Douleur thoracique intense",
        ],
        "general_measures": [
            "Repos suffisant",
            "Hydratation abondante (eau, bouillons)",
            "Aération modérée de la pièce",
            "Surveiller la température toutes les 6h",
            "Consulter si fièvre > 38.5°C persistante ou aggravation",
        ],
        "when_to_seek_care": "Immédiatement si difficultés respiratoires, confusion ou cyanose.",
        "source": "Directives générales académiques (non cliniques)",
    },
    "digestif": {
        "category": "Syndrome digestif",
        "disclaimer": "⚠️ Orientation préliminaire uniquement. Consulter un médecin.",
        "general_info": (
            "Les troubles digestifs courants comprennent nausées, vomissements, "
            "diarrhée, douleurs abdominales et crampes. "
            "La gastro-entérite virale est fréquente et généralement auto-limitée."
        ),
        "red_flags": [
            "Sang dans les selles ou vomissements",
            "Déshydratation sévère (bouche très sèche, absence d'urine > 8h)",
            "Douleur abdominale très intense et localisée",
            "Fièvre > 39°C associée",
            "Signes de choc (pâleur, sueurs froides, pouls rapide)",
        ],
        "general_measures": [
            "Réhydratation orale progressive (eau, solutés de réhydratation)",
            "Alimentation légère : riz, banane, pain grillé, compote",
            "Éviter les produits laitiers et aliments gras temporairement",
            "Repos",
            "Ne pas prendre d'anti-diarrhéiques sans avis médical",
        ],
        "when_to_seek_care": "Si déshydratation, sang visible ou symptômes > 48-72h.",
        "source": "Directives générales académiques (non cliniques)",
    },
    "douleur": {
        "category": "Syndrome douloureux",
        "disclaimer": "⚠️ Orientation préliminaire uniquement. Consulter un médecin.",
        "general_info": (
            "La douleur est un symptôme dont l'évaluation nécessite toujours "
            "un examen clinique par un professionnel de santé. "
            "L'intensité, la localisation et les caractéristiques orientent l'étiologie."
        ),
        "red_flags": [
            "Douleur thoracique irradiant vers le bras gauche ou la mâchoire",
            "Céphalée brutale 'd'une intensité jamais ressentie'",
            "Douleur abdominale en planche avec rigidité",
            "Douleur lombaire avec troubles neurologiques",
            "Douleur post-traumatique avec déformation visible",
        ],
        "general_measures": [
            "Position antalgique de confort",
            "Application de chaud ou froid selon le type (éviter sur peau lésée)",
            "Repos de la zone douloureuse",
            "Éviter les efforts aggravants",
            "Ne pas prendre d'antalgiques sans évaluation médicale préalable",
        ],
        "when_to_seek_care": "Immédiatement si douleur thoracique, neurologique ou post-trauma.",
        "source": "Directives générales académiques (non cliniques)",
    },
    "neurologique": {
        "category": "Symptômes neurologiques",
        "disclaimer": "⚠️ Orientation préliminaire uniquement. Consulter un médecin.",
        "general_info": (
            "Les symptômes neurologiques requièrent une attention médicale rapide. "
            "Céphalées, vertiges, troubles de la vision ou de l'équilibre "
            "doivent être évalués par un médecin."
        ),
        "red_flags": [
            "Céphalée d'apparition brutale et intense",
            "Perte de conscience ou syncope",
            "Troubles de la parole (aphasie)",
            "Paralysie ou faiblesse d'un côté du corps",
            "Confusion ou désorientation soudaine",
            "Convulsions",
        ],
        "general_measures": [
            "Repos dans un endroit calme et sécurisé",
            "Éviter les stimulations lumineuses et sonores intenses",
            "Ne pas prendre de médicaments sans avis médical",
            "Signaler les symptômes à un proche",
        ],
        "when_to_seek_care": "URGENCE si tout signe neurologique focal ou perte de conscience.",
        "source": "Directives générales académiques (non cliniques)",
    },
    "general": {
        "category": "Symptômes généraux",
        "disclaimer": "⚠️ Orientation préliminaire uniquement. Consulter un médecin.",
        "general_info": (
            "En l'absence de catégorie spécifique identifiée, "
            "des mesures générales de confort et de surveillance sont recommandées. "
            "Un médecin doit évaluer tout symptôme persistant ou préoccupant."
        ),
        "red_flags": [
            "Tout symptôme d'apparition brutale et d'intensité sévère",
            "Perte de connaissance",
            "Saignement abondant inexpliqué",
            "Douleur thoracique",
            "Difficultés respiratoires",
        ],
        "general_measures": [
            "Repos",
            "Hydratation correcte",
            "Surveillance de l'évolution des symptômes",
            "Éviter l'automédication",
            "Consulter un médecin si persistance > 48h ou aggravation",
        ],
        "when_to_seek_care": "Consulter dès que possible si doute ou préoccupation.",
        "source": "Directives générales académiques (non cliniques)",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# OUTIL MCP 1 : fetch_medical_guidelines
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def fetch_medical_guidelines(symptom_category: str = "general") -> str:
    """
    Récupère des directives médicales générales pour une catégorie de symptômes.

    Cet outil fournit des informations générales et éducatives sur les symptômes
    courants. Il NE fournit PAS de diagnostic médical.

    Args:
        symptom_category: Catégorie de symptômes. Valeurs acceptées :
            "respiratoire", "digestif", "douleur", "neurologique", "general".
            Par défaut : "general".

    Returns:
        Directives générales structurées en JSON incluant :
        - Informations générales sur la catégorie
        - Signes d'alarme (red flags) à surveiller
        - Mesures générales recommandées
        - Quand consulter un médecin
        - Disclaimer éthique obligatoire
    """
    category = symptom_category.lower().strip()

    # Correspondance flexible
    category_map = {
        "respiratory": "respiratoire",
        "respiration": "respiratoire",
        "toux": "respiratoire",
        "rhume": "respiratoire",
        "grippe": "respiratoire",
        "digestive": "digestif",
        "gastro": "digestif",
        "ventre": "digestif",
        "nausee": "digestif",
        "pain": "douleur",
        "douleurs": "douleur",
        "cephalee": "neurologique",
        "tete": "neurologique",
        "neurologic": "neurologique",
    }

    mapped = category_map.get(category, category)
    guidelines = MEDICAL_GUIDELINES.get(mapped, MEDICAL_GUIDELINES["general"])

    result = {
        "status": "success",
        "category": guidelines["category"],
        "disclaimer": "⚠️ IMPORTANT : « Ce système ne remplace pas une consultation médicale. »",
        "general_info": guidelines["general_info"],
        "red_flags": guidelines["red_flags"],
        "general_measures": guidelines["general_measures"],
        "when_to_seek_care": guidelines["when_to_seek_care"],
        "source": guidelines["source"],
        "retrieved_at": datetime.now().isoformat(),
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# OUTIL MCP 2 : log_consultation
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def log_consultation(thread_id: str, event_type: str, data: str) -> str:
    """
    Enregistre un événement de consultation dans le système de stockage local.

    Chaque consultation est sauvegardée dans un fichier JSON dédié dans
    le répertoire mcp_server/data/. Cela assure la traçabilité académique
    du workflow multi-agents.

    Args:
        thread_id: Identifiant unique de la session de consultation.
        event_type: Type d'événement à enregistrer. Exemples :
            "consultation_start", "question_asked", "answer_received",
            "diagnostic_summary", "physician_review", "report_generated".
        data: Contenu de l'événement à enregistrer (texte libre ou JSON sérialisé).

    Returns:
        Confirmation JSON de l'enregistrement avec timestamp.
    """
    if not thread_id or not event_type:
        return json.dumps({
            "status": "error",
            "message": "thread_id et event_type sont obligatoires.",
        })

    # Fichier de log par session
    log_file = DATA_DIR / f"consultation_{thread_id}.json"

    # Chargement ou initialisation du log existant
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            log_data = json.load(f)
    else:
        log_data = {
            "thread_id": thread_id,
            "created_at": datetime.now().isoformat(),
            "disclaimer": "Exercice académique. Ce système ne remplace pas une consultation médicale.",
            "events": [],
        }

    # Ajout du nouvel événement
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "data": data,
    }
    log_data["events"].append(event)
    log_data["last_updated"] = datetime.now().isoformat()

    # Sauvegarde
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    return json.dumps({
        "status": "success",
        "thread_id": thread_id,
        "event_type": event_type,
        "event_count": len(log_data["events"]),
        "logged_at": event["timestamp"],
        "file": str(log_file),
    }, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# OUTIL MCP 3 : get_consultation_history
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_consultation_history(thread_id: str) -> str:
    """
    Récupère l'historique complet d'une consultation enregistrée.

    Lit le fichier de log correspondant au thread_id et retourne
    tous les événements enregistrés pour cette session.

    Args:
        thread_id: Identifiant unique de la session de consultation.

    Returns:
        Historique complet de la consultation en JSON, ou message d'erreur
        si la consultation n'existe pas.
    """
    if not thread_id:
        return json.dumps({"status": "error", "message": "thread_id obligatoire."})

    log_file = DATA_DIR / f"consultation_{thread_id}.json"

    if not log_file.exists():
        return json.dumps({
            "status": "not_found",
            "thread_id": thread_id,
            "message": f"Aucune consultation trouvée pour le thread_id '{thread_id}'.",
        })

    with open(log_file, "r", encoding="utf-8") as f:
        log_data = json.load(f)

    return json.dumps({
        "status": "success",
        "thread_id": thread_id,
        "consultation": log_data,
    }, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# RESSOURCE MCP : Informations sur le serveur
# ══════════════════════════════════════════════════════════════════════════════

@mcp.resource("medical://guidelines/categories")
def list_guidelines_categories() -> str:
    """
    Ressource MCP listant toutes les catégories de directives disponibles.
    Accessible via l'URI : medical://guidelines/categories
    """
    categories = list(MEDICAL_GUIDELINES.keys())
    return json.dumps({
        "available_categories": categories,
        "description": "Catégories de directives médicales générales disponibles.",
        "disclaimer": "⚠️ À usage académique uniquement. « Ce système ne remplace pas une consultation médicale. »",
    }, ensure_ascii=False, indent=2)


@mcp.resource("medical://server/info")
def server_info() -> str:
    """Informations sur le serveur MCP médical académique."""
    return json.dumps({
        "name": "medical-orientation-mcp",
        "version": "1.0.0",
        "purpose": "Exercice académique - Système Multi-Agents (SMA)",
        "tools": ["fetch_medical_guidelines", "log_consultation", "get_consultation_history"],
        "ethical_notice": "Ce serveur est un composant académique. « Ce système ne remplace pas une consultation médicale. »",
        "data_directory": str(DATA_DIR),
    }, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🏥 Démarrage du serveur MCP d'orientation clinique simulée...")
    print(f"📁 Répertoire de données : {DATA_DIR}")
    print("⚠️  RAPPEL : Ce système est un exercice académique.")
    print("     « Ce système ne remplace pas une consultation médicale. »")
    print("─" * 60)
    # Lancement en mode stdio (compatible LangGraph + MCP clients)
    mcp.run(transport="sse")