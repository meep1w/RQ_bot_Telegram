import secrets
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Tenant
from app.settings import settings

async def create_or_replace_tenant(session: AsyncSession, owner_user_id: int, owner_username: str | None, bot_token: str) -> Tenant:
    # один бот на одного владельца: если есть — обновим токен/секрет
    res = await session.execute(select(Tenant).where(Tenant.owner_user_id == owner_user_id))
    tenant = res.scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(owner_user_id=owner_user_id, owner_username=owner_username, bot_token=bot_token, secret=secrets.token_urlsafe(16), is_active=True)
        session.add(tenant)
    else:
        tenant.bot_token = bot_token
        tenant.is_active = True
        tenant.secret = secrets.token_urlsafe(16)
    await session.flush()
    return tenant

async def get_tenant_by_id(session: AsyncSession, tenant_id: int) -> Tenant | None:
    res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    return res.scalar_one_or_none()

async def delete_tenant(session: AsyncSession, tenant_id: int) -> bool:
    await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
    return True

async def set_tenant_active(session: AsyncSession, tenant_id: int, active: bool) -> None:
    await session.execute(update(Tenant).where(Tenant.id == tenant_id).values(is_active=active))