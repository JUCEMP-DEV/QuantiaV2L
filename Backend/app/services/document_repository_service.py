from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Protocol

from app.core.config import settings
from app.core.supabase_client import get_supabase_admin_client


DOCUMENT_STATUSES = {
    "uploaded",
    "ocr_processing",
    "ocr_completed",
    "indexing",
    "ready",
    "failed",
}


class DocumentRepository(Protocol):
    def create(self, record: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, document_id: str, user_id: str) -> dict[str, Any] | None: ...

    def list(self, user_id: str) -> list[dict[str, Any]]: ...

    def find_by_checksum(self, user_id: str, checksum: str) -> dict[str, Any] | None: ...

    def usage(self, user_id: str) -> tuple[int, int]: ...

    def list_cleanup_candidates(
        self,
        user_id: str,
        *,
        retention_before: datetime | None,
        failed_before: datetime | None,
        limit: int,
    ) -> list[dict[str, Any]]: ...

    def update(self, document_id: str, user_id: str, values: dict[str, Any]) -> dict[str, Any]: ...

    def delete(self, document_id: str, user_id: str) -> dict[str, Any] | None: ...


class LocalDocumentRepository:
    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_record(record, creating=True)
        document_id = str(normalized.get("id") or "").strip()
        if not document_id:
            raise ValueError("document_id es obligatorio.")
        with self._lock:
            if document_id in self._documents:
                raise ValueError("El documento ya existe.")
            self._documents[document_id] = normalized
            return deepcopy(normalized)

    def get(self, document_id: str, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._documents.get(document_id)
            if record is None or record.get("user_id") != user_id:
                return None
            return deepcopy(record)

    def list(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            records = [deepcopy(item) for item in self._documents.values() if item.get("user_id") == user_id]
        return sorted(records, key=lambda item: str(item.get("created_at") or ""), reverse=True)

    def find_by_checksum(self, user_id: str, checksum: str) -> dict[str, Any] | None:
        with self._lock:
            for item in self._documents.values():
                if item.get("user_id") == user_id and item.get("file_checksum") == checksum:
                    return deepcopy(item)
        return None

    def usage(self, user_id: str) -> tuple[int, int]:
        with self._lock:
            records = [item for item in self._documents.values() if item.get("user_id") == user_id]
            return len(records), sum(int(item.get("size_bytes") or 0) for item in records)

    def list_cleanup_candidates(
        self,
        user_id: str,
        *,
        retention_before: datetime | None,
        failed_before: datetime | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        with self._lock:
            for item in self._documents.values():
                if item.get("user_id") != user_id:
                    continue
                created_at = _parse_datetime(item.get("created_at"))
                updated_at = _parse_datetime(item.get("updated_at"))
                expired = retention_before is not None and created_at < retention_before
                failed_expired = (
                    failed_before is not None
                    and item.get("status") == "failed"
                    and updated_at < failed_before
                )
                if expired or failed_expired:
                    candidates.append(deepcopy(item))
                if len(candidates) >= limit:
                    break
        return candidates

    def update(self, document_id: str, user_id: str, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            current = self._documents.get(document_id)
            if current is None or current.get("user_id") != user_id:
                raise KeyError(document_id)
            updated = {**current, **values, "updated_at": _utc_now()}
            _validate_status(updated.get("status"))
            self._documents[document_id] = updated
            return deepcopy(updated)

    def delete(self, document_id: str, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            current = self._documents.get(document_id)
            if current is None or current.get("user_id") != user_id:
                return None
            return deepcopy(self._documents.pop(document_id))

    def clear(self) -> None:
        with self._lock:
            self._documents.clear()


class SupabaseDocumentRepository:
    def __init__(self, table_name: str | None = None) -> None:
        self.table_name = table_name or settings.document_table_name

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_record(record, creating=True)
        result = get_supabase_admin_client().table(self.table_name).insert(normalized).execute()
        if not result.data:
            raise RuntimeError("Supabase no devolvio el documento creado.")
        return dict(result.data[0])

    def get(self, document_id: str, user_id: str) -> dict[str, Any] | None:
        result = (
            get_supabase_admin_client()
            .table(self.table_name)
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return dict(result.data[0]) if result.data else None

    def list(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            get_supabase_admin_client()
            .table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [dict(item) for item in (result.data or [])]

    def find_by_checksum(self, user_id: str, checksum: str) -> dict[str, Any] | None:
        result = (
            get_supabase_admin_client()
            .table(self.table_name)
            .select("*")
            .eq("user_id", user_id)
            .eq("file_checksum", checksum)
            .limit(1)
            .execute()
        )
        return dict(result.data[0]) if result.data else None

    def usage(self, user_id: str) -> tuple[int, int]:
        result = (
            get_supabase_admin_client()
            .table(self.table_name)
            .select("id,size_bytes")
            .eq("user_id", user_id)
            .execute()
        )
        records = result.data or []
        return len(records), sum(int(item.get("size_bytes") or 0) for item in records)

    def list_cleanup_candidates(
        self,
        user_id: str,
        *,
        retention_before: datetime | None,
        failed_before: datetime | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        fields = "id,user_id,storage_bucket,storage_object_path,status,created_at,updated_at"
        records: dict[str, dict[str, Any]] = {}
        client = get_supabase_admin_client().table(self.table_name)
        if retention_before is not None:
            result = (
                client.select(fields)
                .eq("user_id", user_id)
                .lt("created_at", retention_before.isoformat())
                .limit(limit)
                .execute()
            )
            records.update({str(item["id"]): dict(item) for item in (result.data or [])})
        if failed_before is not None and len(records) < limit:
            result = (
                get_supabase_admin_client()
                .table(self.table_name)
                .select(fields)
                .eq("user_id", user_id)
                .eq("status", "failed")
                .lt("updated_at", failed_before.isoformat())
                .limit(limit - len(records))
                .execute()
            )
            records.update({str(item["id"]): dict(item) for item in (result.data or [])})
        return list(records.values())[:limit]

    def update(self, document_id: str, user_id: str, values: dict[str, Any]) -> dict[str, Any]:
        _validate_status(values.get("status"))
        payload = {**values, "updated_at": _utc_now()}
        result = (
            get_supabase_admin_client()
            .table(self.table_name)
            .update(payload)
            .eq("id", document_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise KeyError(document_id)
        return dict(result.data[0])

    def delete(self, document_id: str, user_id: str) -> dict[str, Any] | None:
        result = (
            get_supabase_admin_client()
            .table(self.table_name)
            .delete()
            .eq("id", document_id)
            .eq("user_id", user_id)
            .execute()
        )
        return dict(result.data[0]) if result.data else None


def create_document_repository(backend: str | None = None) -> DocumentRepository:
    selected = (backend or settings.document_persistence_backend).strip().lower()
    if selected == "local":
        return LocalDocumentRepository()
    if selected == "supabase":
        return SupabaseDocumentRepository()
    raise ValueError(f"DOCUMENT_PERSISTENCE_BACKEND no soportado: {selected}")


def _normalize_record(record: dict[str, Any], *, creating: bool) -> dict[str, Any]:
    normalized = deepcopy(record)
    _validate_status(normalized.get("status"))
    now = _utc_now()
    if creating:
        normalized.setdefault("created_at", now)
        normalized.setdefault("updated_at", now)
    else:
        normalized["updated_at"] = now
    return normalized


def _validate_status(value: Any) -> None:
    if value is None:
        return
    if value not in DOCUMENT_STATUSES:
        raise ValueError(f"Estado documental no soportado: {value}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        normalized = str(value or "").strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.max.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
