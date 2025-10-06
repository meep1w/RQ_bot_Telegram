from pydantic import BaseModel

class TenantCreate(BaseModel):
    owner_user_id: int
    owner_username: str | None
    bot_token: str

class TenantOut(BaseModel):
    id: int
    owner_user_id: int
    bot_username: str | None
    is_active: bool