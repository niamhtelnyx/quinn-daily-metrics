"""Entry point when the package is executed as a module."""

import sys

import click
import uvicorn

from .platform.settings import Settings


@click.command()
@click.option("--reload", is_flag=True)
def main(reload=False):
    kwargs = {"reload": reload}

    settings = Settings()

    uvicorn.run(
        "my_agentic_serviceservice_order_specialist:app",
        loop="uvloop",
        factory=True,
        host=settings.app_http.host,
        port=settings.app_http.port,
        log_level=settings.app_http.log_level.lower(),
        **kwargs,
    )


if __name__ == "__main__":
    sys.exit(main())
