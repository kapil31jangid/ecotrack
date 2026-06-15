import os
import logging
from datetime import datetime
from google.cloud import firestore
from google.cloud.firestore import SERVER_TIMESTAMP
from backend.config import GOOGLE_CLOUD_PROJECT, FIRESTORE_COLLECTION

logger = logging.getLogger("ecotrack")

# Initialize AsyncClient if GOOGLE_CLOUD_PROJECT is provided
db = None
try:
    if GOOGLE_CLOUD_PROJECT:
        db = firestore.AsyncClient(project=GOOGLE_CLOUD_PROJECT)
        logger.info(f"Firestore client successfully initialized for project: {GOOGLE_CLOUD_PROJECT}")
    else:
        logger.warning("GOOGLE_CLOUD_PROJECT environment variable not set. Firestore will run in mock mode.")
except Exception as e:
    logger.error(f"Failed to initialize Firestore Client: {str(e)}")

# Local store for fallback mock mode
_local_footprints = {}
_local_chats = {}
_local_analytics = {}

async def save_footprint(session_id: str, input_data: dict, result: dict) -> bool:
    """Save calculation to Firestore with SERVER_TIMESTAMP."""
    doc_data = {
        "session_id": session_id,
        "input_data": input_data,
        "result": result,
    }

    if db:
        try:
            doc_data["timestamp"] = SERVER_TIMESTAMP
            await db.collection(FIRESTORE_COLLECTION).add(doc_data)
            logger.info(f"Successfully saved footprint to Firestore for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving footprint to Firestore: {str(e)}")
            return False
    else:
        # Fallback to local store
        doc_data["timestamp"] = datetime.utcnow().isoformat()
        _local_footprints.setdefault(session_id, []).append(doc_data)
        logger.info(f"Saved footprint to local in-memory store for session: {session_id}")
        return True

async def get_footprint_history(session_id: str) -> list[dict]:
    """Get all records for session ordered by timestamp asc. Return [] if none."""
    if db:
        try:
            query = db.collection(FIRESTORE_COLLECTION).where("session_id", "==", session_id)
            docs = []
            async for doc in query.stream():
                data = doc.to_dict()
                # Resolve SERVER_TIMESTAMP serialization
                ts = data.get("timestamp")
                if ts:
                    if hasattr(ts, "isoformat"):
                        data["timestamp"] = ts.isoformat()
                    else:
                        data["timestamp"] = str(ts)
                docs.append(data)
            
            # Sort by timestamp ascending
            docs.sort(key=lambda x: x.get("timestamp", ""))
            logger.info(f"Successfully retrieved {len(docs)} footprint logs from Firestore for session: {session_id}")
            return docs
        except Exception as e:
            logger.error(f"Error querying footprint history from Firestore: {str(e)}")
            return []
    else:
        records = _local_footprints.get(session_id, [])
        logger.info(f"Retrieved {len(records)} footprint logs from local store for session: {session_id}")
        return sorted(records, key=lambda x: x.get("timestamp", ""))

async def save_chat_message(session_id: str, role: str, content: str, model_used: str = "") -> None:
    """Save chat message to footprints/{session_id}/chat subcollection."""
    msg_data = {
        "role": role,
        "content": content,
        "model_used": model_used,
    }

    if db:
        try:
            msg_data["timestamp"] = SERVER_TIMESTAMP
            await db.collection(FIRESTORE_COLLECTION).document(session_id).collection("chat").add(msg_data)
            logger.info(f"Successfully saved chat message ({role}) to Firestore for session: {session_id}")
        except Exception as e:
            logger.error(f"Error saving chat message to Firestore: {str(e)}")
    else:
        msg_data["timestamp"] = datetime.utcnow().isoformat()
        _local_chats.setdefault(session_id, []).append(msg_data)
        logger.info(f"Saved chat message ({role}) to local store for session: {session_id}")

async def aggregate_weekly_stats() -> dict:
    """
    Compute and store anonymized stats in Firestore 'analytics' collection:
    - total_calculations, avg_co2e_monthly, diet_distribution, top_category
    Return the stats dict.
    """
    all_docs = []
    if db:
        try:
            query = db.collection(FIRESTORE_COLLECTION)
            async for doc in query.stream():
                all_docs.append(doc.to_dict())
        except Exception as e:
            logger.error(f"Error retrieving footprints for weekly aggregation: {str(e)}")
    else:
        for records_list in _local_footprints.values():
            all_docs.extend(records_list)

    total_calculations = len(all_docs)
    
    if total_calculations == 0:
        stats = {
            "total_calculations": 0,
            "avg_co2e_monthly": 0.0,
            "diet_distribution": {"vegan": 0, "vegetarian": 0, "omnivore": 0, "meat_heavy": 0},
            "top_category": "none",
        }
    else:
        co2_sum = 0.0
        diet_counts = {"vegan": 0, "vegetarian": 0, "omnivore": 0, "meat_heavy": 0}
        category_sums = {"transport": 0.0, "diet": 0.0, "energy": 0.0, "shopping": 0.0}

        for doc in all_docs:
            result = doc.get("result", {})
            input_data = doc.get("input_data", {})
            
            co2_sum += result.get("co2e_monthly", 0.0)
            
            diet = input_data.get("diet_type")
            if diet in diet_counts:
                diet_counts[diet] += 1
            
            breakdown = result.get("category_breakdown", {})
            for cat in category_sums:
                category_sums[cat] += breakdown.get(cat, 0.0)

        avg_co2e_monthly = round(co2_sum / total_calculations, 2)
        top_category = max(category_sums, key=category_sums.get)

        stats = {
            "total_calculations": total_calculations,
            "avg_co2e_monthly": avg_co2e_monthly,
            "diet_distribution": diet_counts,
            "top_category": top_category,
        }

    if db:
        try:
            stats["timestamp"] = SERVER_TIMESTAMP
            await db.collection("analytics").document("weekly_summary").set(stats)
            # Fetch for output serialization compatibility
            stats["timestamp"] = datetime.utcnow().isoformat()
            logger.info("Successfully saved aggregated weekly summary to Firestore.")
        except Exception as e:
            logger.error(f"Error writing analytics weekly summary: {str(e)}")
    else:
        stats["timestamp"] = datetime.utcnow().isoformat()
        _local_analytics["weekly_summary"] = stats
        logger.info("Saved weekly summary to local mock database.")

    return stats
