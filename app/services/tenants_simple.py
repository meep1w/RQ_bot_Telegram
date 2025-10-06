import secrets
import asyncpg
from typing import Optional, List, Tuple, Dict, Any
from app.settings import settings

def _dsn() -> str:
    return settings.DATABASE_URL.replace("+asyncpg", "")

# === CRUD для GA и подключения ===

async def get_tenant_by_owner(owner_user_id: int) -> Optional[Dict[str, Any]]:
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        row = await conn.fetchrow("SELECT * FROM tenants WHERE owner_user_id=$1", owner_user_id)
        return dict(row) if row else None
    finally:
        await conn.close()

async def upsert_tenant(owner_user_id: int, owner_username: Optional[str], bot_token: str) -> Tuple[int, str]:
    """
    Если уже есть тенант у owner_user_id — НЕ создаём нового, а просто возвращаем его id/secret.
    (строгое правило 1 владелец → 1 бот)
    """
    existing = await get_tenant_by_owner(owner_user_id)
    if existing:
        return existing["id"], existing["secret"]

    secret = secrets.token_urlsafe(16)
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        tenant_id = await conn.fetchval(
            "INSERT INTO tenants(owner_user_id, owner_username, bot_token, secret, is_active) "
            "VALUES($1,$2,$3,$4,TRUE) RETURNING id",
            owner_user_id, owner_username, bot_token, secret
        )
    finally:
        await conn.close()
    return tenant_id, secret

async def save_bot_username(tenant_id: int, username: str):
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        await conn.execute("UPDATE tenants SET bot_username=$1 WHERE id=$2", username, tenant_id)
    finally:
        await conn.close()

async def get_tenant(tenant_id: int) -> Optional[Dict[str, Any]]:
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        row = await conn.fetchrow("SELECT * FROM tenants WHERE id=$1", tenant_id)
        return dict(row) if row else None
    finally:
        await conn.close()

async def list_tenants(page: int, page_size: int = 10) -> List[Dict[str, Any]]:
    offset = (page-1) * page_size
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        rows = await conn.fetch(
            "SELECT id, owner_user_id, owner_username, bot_username, is_active "
            "FROM tenants ORDER BY id DESC LIMIT $1 OFFSET $2",
            page_size+1, offset
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def delete_tenant(tenant_id: int):
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        await conn.execute("DELETE FROM tenants WHERE id=$1", tenant_id)
    finally:
        await conn.close()
