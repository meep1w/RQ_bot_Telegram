# app/services/channels_simple.py
from typing import List, Dict, Any, Optional
import asyncpg
from app.settings import settings

async def _conn():
    return await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))

async def list_channels(tenant_id: int) -> List[Dict[str, Any]]:
    c = await _conn()
    try:
        rows = await c.fetch(
            "SELECT id, chat_id, title, can_auto_approve FROM channels WHERE tenant_id=$1 ORDER BY id DESC",
            tenant_id,
        )
        return [dict(r) for r in rows]
    finally:
        await c.close()

async def upsert_channel(tenant_id: int, chat_id: int, title: Optional[str]) -> int:
    c = await _conn()
    try:
        row = await c.fetchrow(
            """
            INSERT INTO channels (tenant_id, chat_id, title, can_auto_approve)
            VALUES ($1,$2,$3, true)
            ON CONFLICT (tenant_id, chat_id) DO UPDATE SET title=EXCLUDED.title
            RETURNING id
            """,
            tenant_id, chat_id, title,
        )
        return row["id"]
    finally:
        await c.close()

async def delete_channel(tenant_id: int, channel_id: int) -> None:
    c = await _conn()
    try:
        await c.execute("DELETE FROM channels WHERE id=$1 AND tenant_id=$2", channel_id, tenant_id)
    finally:
        await c.close()
