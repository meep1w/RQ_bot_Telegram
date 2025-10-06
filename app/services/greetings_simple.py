from typing import Optional, Dict, Any
import asyncpg
from app.settings import settings

async def _conn():
    return await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))

async def get_greeting(tenant_id: int, kind: str) -> Optional[Dict[str, Any]]:
    c = await _conn()
    try:
        row = await c.fetchrow(
            "SELECT id, kind, text, button_text, button_url FROM greetings WHERE tenant_id=$1 AND kind=$2",
            tenant_id, kind,
        )
        return dict(row) if row else None
    finally:
        await c.close()

async def upsert_greeting(tenant_id: int, kind: str, text: str,
                          button_text: Optional[str] = None,
                          button_url: Optional[str] = None) -> int:
    c = await _conn()
    try:
        row = await c.fetchrow(
            """
            INSERT INTO greetings (tenant_id, kind, text, button_text, button_url)
            VALUES ($1,$2,$3,$4,$5)
            ON CONFLICT (tenant_id, kind) DO UPDATE
              SET text=EXCLUDED.text, button_text=EXCLUDED.button_text, button_url=EXCLUDED.button_url
            RETURNING id
            """,
            tenant_id, kind, text, button_text, button_url
        )
        return row["id"]
    finally:
        await c.close()
