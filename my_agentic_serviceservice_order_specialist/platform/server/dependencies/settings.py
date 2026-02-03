from fastapi import Request

from my_agentic_serviceservice_order_specialist.platform.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
