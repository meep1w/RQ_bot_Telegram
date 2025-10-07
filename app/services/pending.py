import asyncpg
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.settings import settings

def _dsn() -> str:
    return settings.DATABASE_URL.replace("+asyncpg", "")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pending_requests (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL,
  chat_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status TEXT NOT NULL DEFAULT 'new',   -- new/approved/failed
  dm_ok BOOLEAN,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_pending_tenant_status ON pending_requests(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_pending_tenant_user   ON pending_requests(tenant_id, user_id);
"""

async def ensure_schema():
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        for stmt in CREATE_TABLE_SQL.strip().split(";\n\n"):
            if stmt.strip():
                await conn.execute(stmt)
    finally:
        await conn.close()

async def add_request(tenant_id: int, chat_id: int, user_id: int) -> None:
    await ensure_schema()
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        await conn.execute(
            "INSERT INTO pending_requests(tenant_id, chat_id, user_id) VALUES($1,$2,$3)",
            tenant_id, chat_id, user_id
        )
    finally:
        await conn.close()

async def list_new(tenant_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    await ensure_schema()
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        rows = await conn.fetch(
            "SELECT * FROM pending_requests WHERE tenant_id=$1 AND status='new' ORDER BY requested_at ASC LIMIT $2",
            tenant_id, limit
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def mark_approved(row_id: int, dm_ok: Optional[bool], error: Optional[str]) -> None:
    await ensure_schema()
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        await conn.execute(
            "UPDATE pending_requests SET status='approved', dm_ok=$1, error=$2 WHERE id=$3",
            dm_ok, error, row_id
        )
    finally:
        await conn.close()

async def mark_failed(row_id: int, error: str) -> None:
    await ensure_schema()
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        await conn.execute(
            "UPDATE pending_requests SET status='failed', error=$1 WHERE id=$2",
            error, row_id
        )
    finally:
        await conn.close()
