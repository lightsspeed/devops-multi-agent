import os
import tempfile
import pytest

from devops_agents.storage import FileSessionStorage


def test_session_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileSessionStorage(data_dir=tmpdir)
        session_id = storage.create_session()

        assert session_id.startswith("session-")
        assert storage.session_exists(session_id)
        assert storage.get_session_messages(session_id) == []


def test_session_creation_custom_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileSessionStorage(data_dir=tmpdir)
        session_id = storage.create_session(session_id="custom-session-123")

        assert session_id == "custom-session-123"
        assert storage.session_exists("custom-session-123")


def test_message_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileSessionStorage(data_dir=tmpdir)
        session_id = storage.create_session(session_id="test-session")

        msg1 = storage.add_message(
            session_id=session_id,
            sender="user",
            text="What pods are failing?",
        )
        assert msg1["sender"] == "user"
        assert msg1["text"] == "What pods are failing?"

        msg2 = storage.add_message(
            session_id=session_id,
            sender="assistant",
            text="Pod payment-api is failing with CrashLoopBackOff",
            selected_agent="kubernetes",
        )
        assert msg2["selected_agent"] == "kubernetes"

        messages = storage.get_session_messages(session_id)
        assert len(messages) == 2
        assert messages[0]["text"] == "What pods are failing?"
        assert messages[1]["text"] == "Pod payment-api is failing with CrashLoopBackOff"


def test_loading_existing_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        # First storage instance creates and writes
        storage1 = FileSessionStorage(data_dir=tmpdir)
        session_id = storage1.create_session(session_id="persistent-session")
        storage1.add_message(session_id=session_id, sender="user", text="Hello server")

        # Second storage instance loads from disk (bypassing memory cache)
        storage2 = FileSessionStorage(data_dir=tmpdir)
        assert storage2.session_exists("persistent-session")
        messages = storage2.get_session_messages("persistent-session")
        assert len(messages) == 1
        assert messages[0]["text"] == "Hello server"


def test_new_session_isolation():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileSessionStorage(data_dir=tmpdir)
        s1 = storage.create_session(session_id="session-1")
        s2 = storage.create_session(session_id="session-2")

        storage.add_message(session_id=s1, sender="user", text="Session 1 query")
        storage.add_message(session_id=s2, sender="user", text="Session 2 query")

        msgs_1 = storage.get_session_messages(s1)
        msgs_2 = storage.get_session_messages(s2)

        assert len(msgs_1) == 1
        assert msgs_1[0]["text"] == "Session 1 query"

        assert len(msgs_2) == 1
        assert msgs_2[0]["text"] == "Session 2 query"
