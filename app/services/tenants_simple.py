import secrets
import asyncpg
from typing import Optional
from app.settings import settings

def _dsn() -> str:
    # SQLAlchemy-стиль -> asyncpg-стиль
    return settings.DATABASE_URL.replace("+asyncpg", "")

async def upsert_tenant(owner_user_id: int, owner_username: Optional[str], bot_token: str):
    secret = secrets.token_urlsafe(16)
    conn = await asyncpg.connect(dsn=_dsn())
    try:
        row = await conn.fetchrow("SELECT id FROM tenants WHERE owner_user_id=$1", owner_user_id)
        if row:
            await conn.execute(
                "UPDATE tenants SET bot_token=$1, owner_username=$2, secret=$3, is_active=TRUE WHERE id=$4",
                bot_token, owner_username, secret, row["id"]
            )
            tenant_id = row["id"]
        else:
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
