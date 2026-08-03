import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_guest_cannot_create_workspace():
    response = client.post("/api/v1/workspaces", json={"name": "Guest Workspace"})
    assert response.status_code == 401


def test_guest_cannot_list_workspaces():
    response = client.get("/api/v1/workspaces")
    assert response.status_code == 401


def test_authenticated_user_create_and_list_workspace(monkeypatch):
    from app.core import auth

    # Mock user verification
    mock_user = auth.User(id="user_101", email="user101@example.com", full_name="User 101", password_hash="")
    monkeypatch.setattr(auth, "_verify_supabase_token", lambda token: mock_user)

    # Mock Supabase database client
    workspaces_db = []
    members_db = []

    class MockExecute:
        def __init__(self, data):
            self.data = data

    class MockTable:
        def __init__(self, table_name):
            self.table_name = table_name
            self._query = {}
            self._insert_data = None

        def select(self, fields):
            return self

        def eq(self, field, value):
            self._query[field] = value
            return self

        def in_(self, field, values):
            self._query[f"{field}__in"] = values
            return self

        def insert(self, data):
            self._insert_data = data
            return self

        def execute(self):
            if self._insert_data is not None:
                if self.table_name == "workspaces":
                    row = {
                        "id": f"ws-{len(workspaces_db)+1}",
                        "name": self._insert_data["name"],
                        "slug": self._insert_data["slug"],
                        "owner_id": self._insert_data["owner_id"],
                        "created_at": "2026-08-03T00:00:00Z",
                        "updated_at": "2026-08-03T00:00:00Z",
                    }
                    workspaces_db.append(row)
                    return MockExecute([row])
                elif self.table_name == "workspace_members":
                    row = {
                        "id": f"wm-{len(members_db)+1}",
                        "workspace_id": self._insert_data["workspace_id"],
                        "user_id": self._insert_data["user_id"],
                        "role": self._insert_data["role"],
                        "created_at": "2026-08-03T00:00:00Z",
                    }
                    members_db.append(row)
                    return MockExecute([row])

            if self.table_name == "workspaces":
                if "slug" in self._query:
                    res = [w for w in workspaces_db if w["slug"] == self._query["slug"]]
                elif "id__in" in self._query:
                    res = [w for w in workspaces_db if w["id"] in self._query["id__in"]]
                elif "id" in self._query:
                    res = [w for w in workspaces_db if w["id"] == self._query["id"]]
                else:
                    res = workspaces_db
                return MockExecute(res)
            elif self.table_name == "workspace_members":
                if "user_id" in self._query:
                    res = [m for m in members_db if m["user_id"] == self._query["user_id"]]
                elif "workspace_id" in self._query and "user_id" in self._query:
                    res = [
                        m for m in members_db
                        if m["workspace_id"] == self._query["workspace_id"] and m["user_id"] == self._query["user_id"]
                    ]
                else:
                    res = members_db
                return MockExecute(res)

    class MockClient:
        def table(self, name):
            return MockTable(name)

    monkeypatch.setattr("app.api.v1.routes.workspaces.create_supabase_client", lambda token=None: MockClient())
    monkeypatch.setattr("app.core.auth.create_supabase_client", lambda token=None: MockClient())

    headers = {"Authorization": "Bearer valid_token"}

    # 1. Create Workspace
    resp = client.post("/api/v1/workspaces", json={"name": "Alpha Corp", "slug": "alpha-corp"}, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Alpha Corp"
    assert data["slug"] == "alpha-corp"
    assert data["role"] == "owner"
    created_ws_id = data["id"]

    # 2. Duplicate slug attempt
    dup_resp = client.post("/api/v1/workspaces", json={"name": "Alpha Corp Duplicate", "slug": "alpha-corp"}, headers=headers)
    assert dup_resp.status_code == 409

    # 3. List workspaces for creator
    list_resp = client.get("/api/v1/workspaces", headers=headers)
    assert list_resp.status_code == 200
    workspaces = list_resp.json()
    assert len(workspaces) == 1
    assert workspaces[0]["id"] == created_ws_id

    # 4. Get specific workspace detail
    get_resp = client.get(f"/api/v1/workspaces/{created_ws_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == created_ws_id


def test_cross_tenant_isolation(monkeypatch):
    from app.core import auth

    # Mock user verification for User 2 (not a member)
    mock_user2 = auth.User(id="user_202", email="user202@example.com", full_name="User 202", password_hash="")
    monkeypatch.setattr(auth, "_verify_supabase_token", lambda token: mock_user2)

    workspaces_db = [{"id": "ws-private", "name": "Private WS", "slug": "private-ws", "owner_id": "user_101"}]
    members_db = [{"workspace_id": "ws-private", "user_id": "user_101", "role": "owner"}]

    class MockExecute:
        def __init__(self, data):
            self.data = data

    class MockTable:
        def __init__(self, table_name):
            self.table_name = table_name
            self._query = {}

        def select(self, fields):
            return self

        def eq(self, field, value):
            self._query[field] = value
            return self

        def execute(self):
            if self.table_name == "workspaces":
                res = [w for w in workspaces_db if w["id"] == self._query.get("id")]
                return MockExecute(res)
            elif self.table_name == "workspace_members":
                res = [
                    m for m in members_db
                    if m["workspace_id"] == self._query.get("workspace_id") and m["user_id"] == self._query.get("user_id")
                ]
                return MockExecute(res)

    class MockClient:
        def table(self, name):
            return MockTable(name)

    monkeypatch.setattr("app.core.auth.create_supabase_client", lambda token=None: MockClient())

    headers = {"Authorization": "Bearer user2_token"}

    # User 2 tries to access User 1's workspace -> should be 403 Forbidden
    resp = client.get("/api/v1/workspaces/ws-private", headers=headers)
    assert resp.status_code == 403
