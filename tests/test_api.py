"""Mocked API tests: no test calls Azure."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend import main


class FakeVMService:
    def __init__(self):
        self.calls = []

    def get_vm_status(self):
        self.calls.append("status")
        return "VM running"

    def start_vm(self):
        self.calls.append("start")
        return "VM D365DEVVM01 started."

    def stop_vm(self):
        self.calls.append("stop")
        return "VM D365DEVVM01 stopped successfully."


@pytest.fixture
def client(monkeypatch):
    fake = FakeVMService()
    monkeypatch.setattr(main, "vm_service", fake)
    monkeypatch.setattr(main, "settings", replace(main.settings, vm_name="D365DEVVM01"))
    main.pending_stop = False
    with TestClient(main.app) as test_client:
        yield test_client, fake
    main.pending_stop = False


def test_health_endpoint(client):
    response = client[0].get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_chat_status_command(client):
    response = client[0].post("/chat", json={"message": "What is the VM status?"})
    assert response.json()["reply"] == "VM running"
    assert response.json()["action"] == "status"
    assert client[1].calls == ["status"]


def test_start_command(client):
    response = client[0].post("/chat", json={"message": "Start my DEV VM"})
    assert response.json()["success"] is True
    assert response.json()["action"] == "start"
    assert client[1].calls == ["start"]


def test_stop_requires_confirmation(client):
    response = client[0].post("/chat", json={"message": "Stop my DEV VM"})
    assert response.json()["requires_confirmation"] is True
    assert "D365DEVVM01" in response.json()["reply"]
    assert client[1].calls == []


def test_stop_confirmation_calls_azure(client):
    client[0].post("/chat", json={"message": "Stop my DEV VM"})
    response = client[0].post("/chat", json={"message": "Yes"})
    assert response.json()["success"] is True
    assert response.json()["action"] == "stop"
    assert client[1].calls == ["stop"]


def test_stop_cancellation_does_not_call_azure(client):
    client[0].post("/chat", json={"message": "Stop my DEV VM"})
    response = client[0].post("/chat", json={"message": "No"})
    assert response.json()["success"] is True
    assert "cancelled" in response.json()["reply"]
    assert client[1].calls == []


def test_invalid_command(client):
    response = client[0].post("/chat", json={"message": "Delete the database"})
    assert response.json()["success"] is False
    assert response.json()["action"] is None
    assert client[1].calls == []


def test_service_error_is_safe(client, monkeypatch):
    def fail():
        raise main.VMServiceError("Unable to reach Azure.", "network_error")

    monkeypatch.setattr(client[1], "get_vm_status", fail)
    response = client[0].post("/chat", json={"message": "status"})
    assert response.json()["success"] is False
    assert response.json()["reply"] == "Unable to reach Azure."
    assert "traceback" not in response.text.lower()
