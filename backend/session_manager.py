import os
import pickle
from typing import Dict, Any, Optional

# Almacenamiento por sesión
SESSIONS: Dict[str, Dict[str, Any]] = {}

def session_path(session_id: str) -> str:
    """Get the file path for a session"""
    return os.path.join(os.path.dirname(__file__), f"document_store_{session_id}.pkl")

def save_session(session_id: str):
    """Save session data to file"""
    db = SESSIONS.get(session_id)
    if not db:
        return
    try:
        with open(session_path(session_id), 'wb') as f:
            pickle.dump(db, f)
    except Exception as e:
        print(f"Error guardando sesión {session_id}: {e}")

def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Load session data from file"""
    if session_id in SESSIONS:
        return SESSIONS[session_id]
    path = session_path(session_id)
    if os.path.exists(path):
        try:
            with open(path, 'rb') as f:
                SESSIONS[session_id] = pickle.load(f)
                return SESSIONS[session_id]
        except Exception as e:
            print(f"Error cargando sesión {session_id}: {e}")
            return None
    return None

def create_session(session_id: str, db: Dict[str, Any]):
    """Create a new session"""
    SESSIONS[session_id] = db
    save_session(session_id)

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data"""
    return load_session(session_id)

def delete_session(session_id: str):
    """Delete a session"""
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    
    path = session_path(session_id)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            print(f"Error eliminando archivo de sesión {session_id}: {e}")

def list_sessions() -> list:
    """List all active sessions"""
    return list(SESSIONS.keys())
