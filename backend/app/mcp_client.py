"""
backend/app/mcp_client.py - Client MCP pour les agents LangGraph

Ce module fournit une interface pour que les agents LangGraph puissent
appeler les outils exposés par le serveur MCP (mcp_server/server.py).

En mode académique, le client MCP peut fonctionner en deux modes :
    1. Mode MCP natif : via subprocess + stdio avec le MCP SDK
    2. Mode fallback local : appel direct aux fonctions Python si MCP indisponible

⚠️  Ce module est un exercice académique.
    « Ce système ne remplace pas une consultation médicale. »
"""

import json
import subprocess
import sys
from pathlib import Path
from langchain_core.tools import tool

# ── Chemin vers le serveur MCP ────────────────────────────────────────────────
MCP_SERVER_PATH = Path(__file__).parents[3] / "mcp_server" / "server.py"


# ══════════════════════════════════════════════════════════════════════════════
# TOOLS LANGCHAIN qui wrappent les outils MCP
# Ces tools sont utilisables directement par les agents LangGraph
# ══════════════════════════════════════════════════════════════════════════════

@tool
def mcp_fetch_medical_guidelines(symptom_category: str = "general") -> str:
    """
    [MCP Tool] Récupère des directives médicales générales depuis le serveur MCP.

    Appelle le tool `fetch_medical_guidelines` du serveur MCP pour obtenir
    des informations générales sur une catégorie de symptômes.

    Args:
        symptom_category: Catégorie de symptômes.
            Options : "respiratoire", "digestif", "douleur", "neurologique", "general".

    Returns:
        Directives médicales générales structurées en JSON.
        ⚠️ Uniquement à titre informatif académique.
        « Ce système ne remplace pas une consultation médicale. »
    """
    try:
        return _call_mcp_tool("fetch_medical_guidelines", {
            "symptom_category": symptom_category
        })
    except Exception as e:
        # Fallback : import direct de la fonction Python
        return _fallback_fetch_guidelines(symptom_category, str(e))


@tool
def mcp_log_consultation(thread_id: str, event_type: str, data: str) -> str:
    """
    [MCP Tool] Enregistre un événement de consultation via le serveur MCP.

    Sauvegarde les données de consultation dans mcp_server/data/
    pour assurer la traçabilité académique du workflow.

    Args:
        thread_id: Identifiant unique de la session.
        event_type: Type d'événement (ex: "question_asked", "diagnostic_summary").
        data: Contenu à enregistrer.

    Returns:
        Confirmation JSON de l'enregistrement.
    """
    try:
        return _call_mcp_tool("log_consultation", {
            "thread_id": thread_id,
            "event_type": event_type,
            "data": data,
        })
    except Exception as e:
        return json.dumps({
            "status": "fallback",
            "message": f"MCP indisponible, log ignoré. Erreur : {e}",
            "thread_id": thread_id,
            "event_type": event_type,
        })


@tool
def mcp_get_consultation_history(thread_id: str) -> str:
    """
    [MCP Tool] Récupère l'historique d'une consultation via le serveur MCP.

    Args:
        thread_id: Identifiant unique de la session de consultation.

    Returns:
        Historique complet de la consultation en JSON.
    """
    try:
        return _call_mcp_tool("get_consultation_history", {"thread_id": thread_id})
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Impossible de récupérer l'historique. Erreur : {e}",
            "thread_id": thread_id,
        })


# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS INTERNES
# ══════════════════════════════════════════════════════════════════════════════

def _call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """
    Appelle un outil MCP via le protocole MCP over stdio.

    Cette implémentation utilise le client MCP Python SDK pour
    communiquer avec le serveur via subprocess.

    Args:
        tool_name: Nom de l'outil MCP à appeler.
        arguments: Arguments à passer à l'outil.

    Returns:
        Résultat de l'outil sous forme de chaîne.
    """
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        import asyncio

        async def _async_call():
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[str(MCP_SERVER_PATH)],
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    if result.content:
                        return result.content[0].text
                    return json.dumps({"status": "empty_response"})

        return asyncio.run(_async_call())

    except ImportError:
        raise RuntimeError("MCP SDK non disponible. Installez : pip install mcp")
    except Exception as e:
        raise RuntimeError(f"Erreur appel MCP tool '{tool_name}': {e}")


def _fallback_fetch_guidelines(symptom_category: str, error_msg: str) -> str:
    """
    Fallback Python direct si le serveur MCP est indisponible.
    Importe et appelle directement la fonction depuis mcp_server/server.py.
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mcp_server", MCP_SERVER_PATH)
        if spec and spec.loader:
            module = importlib.util.load_from_spec(spec)
            spec.loader.exec_module(module)
            return module.fetch_medical_guidelines(symptom_category)
    except Exception:
        pass

    # Fallback ultime : réponse générique
    return json.dumps({
        "status": "fallback",
        "category": "general",
        "disclaimer": "⚠️ « Ce système ne remplace pas une consultation médicale. »",
        "general_info": "Directives générales : repos, hydratation, surveillance.",
        "red_flags": ["Difficultés respiratoires", "Douleur thoracique", "Perte de conscience"],
        "general_measures": ["Repos", "Hydratation", "Surveiller l'évolution"],
        "when_to_seek_care": "Consulter un médecin si aggravation ou persistance des symptômes.",
        "note": f"Serveur MCP indisponible : {error_msg}",
    }, ensure_ascii=False, indent=2)


# ── Liste des tools MCP pour les agents ──────────────────────────────────────
MCP_TOOLS = [
    mcp_fetch_medical_guidelines,
    mcp_log_consultation,
    mcp_get_consultation_history,
]