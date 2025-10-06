from fastapi import APIRouter, Response

router = APIRouter()

@router.post("/webhook/child/{tenant_id:int}/{secret}")
async def webhook_child(tenant_id: int, secret: str):
    # TODO: подключить диспетчер дочернего бота
    return Response(status_code=200)
