from __future__ import annotations
from typing import Optional, Dict, Any
import asyncpg
import json
from app.settings import settings


async def _conn():
    # asyncpg строка без +asyncpg
    return await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))


def _to_dict(maybe_json: Any) -> Dict[str, Any]:
    if maybe_json is None:
        return {}
    if isinstance(maybe_json, dict):
        return maybe_json
    if isinstance(maybe_json, (bytes, bytearray)):
        try:
            return json.loads(maybe_json.decode("utf-8"))
        except Exception:
            return {}
    if isinstance(maybe_json, str):
        try:
            return json.loads(maybe_json)
        except Exception:
            return {}
    return {}


def _norm(row: Optional[asyncpg.Record]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    extra = _to_dict(row["extra"])
    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "kind": row["kind"],               # "hello" | "bye"
        "text": row["text"],
        "button_text": row["button_text"],
        "button_url": row["button_url"],
        "photo_file_id": row["photo_file_id"],
        "video_note_file_id": row["video_note_file_id"],
        # из extra:
        "video_file_id": extra.get("video_file_id"),
        "button_kind": extra.get("button_kind", "start"),  # "start" | "url"
    }


async def get_greeting(tenant_id: int, kind: str) -> Optional[Dict[str, Any]]:
    c = await _conn()
    try:
        row = await c.fetchrow(
            """
            SELECT id, tenant_id, kind, text, button_text, button_url,
                   photo_file_id, video_note_file_id, extra
            FROM greetings WHERE tenant_id=$1 AND kind=$2
            """,
            tenant_id, kind,
        )
        return _norm(row)
    finally:
        await c.close()


async def _upsert_full(
    tenant_id: int,
    kind: str,
    *,
    text: Optional[str] = None,
    button_text: Optional[str] = None,
    button_url: Optional[str] = None,
    photo_file_id: Optional[str] = None,
    video_note_file_id: Optional[str] = None,
    video_file_id: Optional[str] = None,
    button_kind: Optional[str] = None,  # "start" | "url"
) -> None:
    # достаём текущую запись и мерджим значения
    cur = await get_greeting(tenant_id, kind)
    text = text if text is not None else (cur or {}).get("text")
    button_text = button_text if button_text is not None else (cur or {}).get("button_text")
    button_url = button_url if button_url is not None else (cur or {}).get("button_url")
    photo_file_id = photo_file_id if photo_file_id is not None else (cur or {}).get("photo_file_id")
    video_note_file_id = video_note_file_id if video_note_file_id is not None else (cur or {}).get("video_note_file_id")
    video_file_id = video_file_id if video_file_id is not None else (cur or {}).get("video_file_id")
    button_kind = button_kind if button_kind is not None else (cur or {}).get("button_kind", "start")

    extra = {"video_file_id": video_file_id, "button_kind": button_kind}
    extra_json = json.dumps(extra, ensure_ascii=False)

    c = await _conn()
    try:
        await c.execute(
            """
            INSERT INTO greetings
                (tenant_id, kind, text, button_text, button_url,
                 photo_file_id, video_note_file_id, extra)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
            ON CONFLICT (tenant_id, kind) DO UPDATE SET
              text=EXCLUDED.text,
              button_text=EXCLUDED.button_text,
              button_url=EXCLUDED.button_url,
              photo_file_id=EXCLUDED.photo_file_id,
              video_note_file_id=EXCLUDED.video_note_file_id,
              extra=EXCLUDED.extra
            """,
            tenant_id, kind, text, button_text, button_url,
            photo_file_id, video_note_file_id, extra_json,
        )
    finally:
        await c.close()


# ===== setters / helpers =====

async def set_text(tenant_id: int, kind: str, text: str) -> None:
    await _upsert_full(tenant_id, kind, text=text)

async def set_photo(tenant_id: int, kind: str, file_id: Optional[str]) -> None:
    await _upsert_full(tenant_id, kind, photo_file_id=file_id, video_file_id=None, video_note_file_id=None)

async def set_video(tenant_id: int, kind: str, file_id: Optional[str]) -> None:
    await _upsert_full(tenant_id, kind, video_file_id=file_id, photo_file_id=None, video_note_file_id=None)

async def set_video_note(tenant_id: int, kind: str, file_id: Optional[str]) -> None:
    await _upsert_full(tenant_id, kind, video_note_file_id=file_id, photo_file_id=None, video_file_id=None)

async def clear_media(tenant_id: int, kind: str) -> None:
    await _upsert_full(tenant_id, kind, photo_file_id=None, video_file_id=None, video_note_file_id=None)

async def set_button_start(tenant_id: int, kind: str, text: str) -> None:
    await _upsert_full(tenant_id, kind, button_text=text, button_kind="start", button_url=None)

async def set_button_url(tenant_id: int, kind: str, text: str, url: str) -> None:
    await _upsert_full(tenant_id, kind, button_text=text, button_kind="url", button_url=url)

async def clear_button(tenant_id: int, kind: str) -> None:
    await _upsert_full(tenant_id, kind, button_text=None, button_url=None, button_kind="start")
