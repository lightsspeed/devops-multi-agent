import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class BaseSessionStorage:
    """Abstract interface for session storage. Can be implemented with SQL/NoSQL in the future."""

    def create_session(self, session_id: Optional[str] = None) -> str:
        raise NotImplementedError

    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def add_message(
        self,
        session_id: str,
        sender: str,
        text: str,
        selected_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def session_exists(self, session_id: str) -> bool:
        raise NotImplementedError


class FileSessionStorage(BaseSessionStorage):
    """File-based local JSON session storage implementation."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, "data", "sessions")
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self._memory_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _get_filepath(self, session_id: str) -> str:
        # Sanitize filename
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.data_dir, f"{safe_id}.json")

    def session_exists(self, session_id: str) -> bool:
        if session_id in self._memory_cache:
            return True
        return os.path.exists(self._get_filepath(session_id))

    def create_session(self, session_id: Optional[str] = None) -> str:
        if not session_id:
            session_id = f"session-{uuid.uuid4().hex[:10]}"
        
        filepath = self._get_filepath(session_id)
        if not os.path.exists(filepath):
            data = {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "messages": [],
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._memory_cache[session_id] = []
        return session_id

    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        if session_id in self._memory_cache:
            return self._memory_cache[session_id]

        filepath = self._get_filepath(session_id)
        if not os.path.exists(filepath):
            return []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                messages = data.get("messages", [])
                self._memory_cache[session_id] = messages
                return messages
        except Exception:
            return []

    def add_message(
        self,
        session_id: str,
        sender: str,
        text: str,
        selected_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.session_exists(session_id):
            self.create_session(session_id)

        messages = self.get_session_messages(session_id)
        msg_obj = {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "sender": sender,
            "text": text,
            "selected_agent": selected_agent,
            "timestamp": datetime.now().strftime("%I:%M %p"),
        }
        messages.append(msg_obj)
        self._memory_cache[session_id] = messages

        filepath = self._get_filepath(session_id)
        try:
            data = {
                "session_id": session_id,
                "updated_at": datetime.utcnow().isoformat(),
                "messages": messages,
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error persisting session message: {e}")

        return msg_obj


# Global singleton instance for storage
storage = FileSessionStorage()
