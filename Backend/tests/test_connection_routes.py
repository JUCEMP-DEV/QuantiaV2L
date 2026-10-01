from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.v1.endpoints import auth, catalogos
from app.core.document_auth import DocumentPrincipal, get_document_principal


def client_for(router):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app, TestClient(app)


def test_profile_requires_session():
    app, client = client_for(auth.router)
    assert client.post("/api/auth/profile/update", json={"user_id": "other"}).status_code == 401


def test_profile_cannot_target_other_user(monkeypatch):
    app, client = client_for(auth.router)
    app.dependency_overrides[get_document_principal] = lambda: DocumentPrincipal("self", "self@example.com")
    def forbidden():
        raise AssertionError("Database must not be contacted")
    monkeypatch.setattr(auth, "get_supabase_admin_client", forbidden)
    assert client.post("/api/auth/profile/update", json={"user_id": "other"}).status_code == 403


def test_profile_uses_session_and_preserves_access_profile(monkeypatch):
    app, client = client_for(auth.router)
    app.dependency_overrides[get_document_principal] = lambda: DocumentPrincipal("self", "self@example.com")
    updates, filters = [], []
    class DB:
        def table(self, name): return self
        def select(self, fields): return self
        def eq(self, key, value):
            filters.append((key, value)); return self
        def limit(self, n): return self
        def update(self, data):
            updates.append(data); return self
        def execute(self):
            return SimpleNamespace(data=[{"id": "self", "nombre": "User", "email": "self@example.com", "perfil": "oficial", "is_active": True}])
    monkeypatch.setattr(auth, "get_supabase_admin_client", lambda: DB())
    result = client.post("/api/auth/profile/update", json={"user_id": "self", "nombre": "Updated", "tipo_usuario": "tecnico"})
    assert result.status_code == 200
    assert updates == [{"nombre": "Updated"}]
    assert all(pair == ("id", "self") for pair in filters)


def test_catalog_projection_and_failure(monkeypatch):
    app, client = client_for(catalogos.router)
    tables = []
    class DB:
        def table(self, name): tables.append(name); return self
        def select(self, fields):
            assert "password" not in fields; return self
        def order(self, field): return self
        def limit(self, n): return self
        def execute(self): return SimpleNamespace(data=[{"id": "example"}])
    monkeypatch.setattr(catalogos, "get_supabase_admin_client", lambda: DB())
    r = client.get("/api/catalogos/reglas-catalogos")
    assert r.status_code == 200
    assert tables == ["engine_activation_rules", "catalog_concepts"]
    assert r.json()["errors"] == []
    def fail(): raise RuntimeError("secret connection details")
    monkeypatch.setattr(catalogos, "get_supabase_admin_client", fail)
    r = client.get("/api/catalogos/reglas-catalogos")
    assert r.status_code == 503
    assert "secret" not in r.text


def test_quotes_require_auth_and_scope_reads(monkeypatch):
    from app.api.v1.endpoints import cotizaciones
    app, client = client_for(cotizaciones.router)
    assert client.get("/api/cotizaciones").status_code == 401
    assert client.get("/api/cotizaciones/other").status_code == 401
    app.dependency_overrides[get_document_principal] = lambda: DocumentPrincipal("self", "self@example.com")
    filters = []
    class DB:
        def table(self, name): return self
        def select(self, fields): return self
        def eq(self, key, value): filters.append((key, value)); return self
        def order(self, *args, **kwargs): return self
        def limit(self, n): return self
        def execute(self): return SimpleNamespace(data=[])
    monkeypatch.setattr(cotizaciones, "get_supabase_admin_client", lambda: DB())
    assert client.get("/api/cotizaciones").status_code == 200
    assert ("user_email", "self@example.com") in filters
    assert client.get("/api/cotizaciones?user_email=other@example.com").status_code == 403
    assert client.get("/api/cotizaciones/other").status_code == 404
    assert client.post("/api/cotizaciones", json={"user_email":"other@example.com"}).status_code == 403
