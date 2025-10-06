from __future__ import annotations
from typing import Optional, List, Dict, Any
import asyncpg
from app.settings import settings

async def _conn():
    # для asyncpg нужна строка без суффикса +asyncpg
    dsn = settings.DATABASE_URL.replace("+asyncpg", "")
    return await asyncpg.connect(dsn)

async def add_channel_by_id(tenant_id: int, chat_id: int, title: Optional[str]) -> int:
    """
    Добавляет или обновляет запись о канале/чате для тенанта.
    Уникальность: (tenant_id, chat_id).
    Возвращает id записи.
    """
    c = await _conn()
    try:
        row = await c.fetchrow(
            """
            INSERT INTO channels (tenant_id, chat_id, title, can_auto_approve)
            VALUES ($1, $2, $3, TRUE)
            ON CONFLICT (tenant_id, chat_id) DO UPDATE SET
                title = COALESCE(EXCLUDED.title, channels.title),
                can_auto_approve = channels.can_auto_approve
            RETURNING id
            """,
            tenant_id, chat_id, title
        )
        return int(row["id"])
    finally:
        await c.close()

async def list_channels(tenant_id: int) -> List[Dict[str, Any]]:
    """
    Список всех подключённых чатов/каналов для тенанта.
    """
    c = await _conn()
    try:
        rows = await c.fetch(
            """
            SELECT id, chat_id, title, can_auto_approve
            FROM channels
            WHERE tenant_id = $1
            ORDER BY id DESC
            """,
            tenant_id
        )
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append({
                "id": int(r["id"]),
                "chat_id": int(r["chat_id"]),
                "title": r["title"],
                "can_auto_approve": bool(r["can_auto_approve"]),
            })
        return out
    finally:
        await c.close()

async def delete_channel(tenant_id: int, channel_row_id: int) -> None:
    """
    Удаляет запись о канале по её первичному id (а не по chat_id),
    дополнительно фильтруя по tenant_id.
    """
    c = await _conn()
    try:
        await c.execute(
            "DELETE FROM channels WHERE id=$1 AND tenant_id=$2",
            channel_row_id, tenant_id
        )
    finally:
        await c.close()

# Доп. настройка, если понадобится в будущем
async def set_can_auto_approve(tenant_id: int, channel_row_id: int, enabled: bool) -> None:
    c = await _conn()
    try:
        await c.execute(
            "UPDATE channels SET can_auto_approve=$1 WHERE id=$2 AND tenant_id=$3",
            enabled, channel_row_id, tenant_id
        )
    finally:
        await c.close()
