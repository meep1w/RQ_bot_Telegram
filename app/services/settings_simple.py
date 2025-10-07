import asyncpg
from typing import Optional
from app.settings import settings

def _dsn() -> str:
    return settings.DATABASE_URL.replace("+asyncpg", "")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tenant_settings (
  tenant_id INTEGER PRIMARY KEY,
  collect_requests BOOLEAN NOT NULL DEFAULT FALSE
);
"""

async def ensure_schema():
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        await conn.execute(CREATE_TABLE_SQL)
    finally:
        await conn.close()

async def get_collect_requests(tenant_id: int) -> bool:
    await ensure_schema()
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        row = await conn.fetchrow("SELECT collect_requests FROM tenant_settings WHERE tenant_id=$1", tenant_id)
        return bool(row["collect_requests"]) if row else False
    finally:
        await conn.close()

async def set_collect_requests(tenant_id: int, value: bool) -> None:
    await ensure_schema()
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        await conn.execute(
            """
            INSERT INTO tenant_settings(tenant_id, collect_requests)
            VALUES($1, $2)
            ON CONFLICT (tenant_id) DO UPDATE SET collect_requests=EXCLUDED.collect_requests
            """,
            tenant_id, value,
        )
    finally:
        await conn.close()

async def toggle_collect_requests(tenant_id: int) -> bool:
    cur = await get_collect_requests(tenant_id)
    nxt = not cur
    await set_collect_requests(tenant_id, nxt)
    return nxt
