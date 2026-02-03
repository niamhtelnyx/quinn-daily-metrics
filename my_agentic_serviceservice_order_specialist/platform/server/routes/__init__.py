from fastapi import APIRouter

from my_agentic_serviceservice_order_specialist.platform.server.routes.base import base_router

root = APIRouter()
root.include_router(base_router)
