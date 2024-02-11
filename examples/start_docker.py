import docker
import os
import logging
import asyncio
from aiohttp import ClientSession

from eufy_security_ws_python.client import WebsocketClient
from eufy_security_ws_python.errors import CannotConnectError

docker_client = docker.from_env()
CONTAINER_ID = "eufy_security_ws"

_LOGGER = logging.getLogger()

STATIONS = "000000:192.168.1.125" #format is SN:IP

async def main() -> None:
    #TODO:
    container = docker_client.containers.run("alpine", "echo hello world", detach=True)
    container = docker_client.containers.run(
        environment=[
            "USERNAME={}".format(os.getenv("EUFY_EMAIL", "mail@example.org")),
            "PASSWORD={}".format(os.getenv("EUFY_PASSWORD", "password")),
            "POLLING_INTERVAL={}".format(os.getenv("POLLING_INTERVAL", "10")),
            "COUNTRY={}".format(os.getenv("COUNTRY_CODE", "DE")),
            "LANGUAGE={}".format(os.getenv("LANGUAGE_CODE", "en")),
            "ACCEPT_INVITATIONS={}".format(os.getenv("ACCEPT_INVITATIONS", "false")),
            "STATION_IP_ADRESSES={}".format(STATIONS),
            "PORT={}".format(os.getenv("CONTAINER_WS_PORT", "3000"))
            ],
        image="bropat/eufy_security_ws",
        detach=True,
        name=CONTAINER_ID,
        network="host",
        volumes={"{}_data".format(CONTAINER_ID): {"bind": "/data", "mode": "rw"}}
    )

    _LOGGER.debug(container.logs())

    async with ClientSession() as session:
        client = WebsocketClient("ws://localhost:{}".format(os.getenv("CONTAINER_WS_PORT", "3000")), session)

        try:
            await client.async_connect()
        except CannotConnectError as err:
            _LOGGER.error("There was a error while connecting to the server: %s", err)
            return

        driver_ready = asyncio.Event()
        await client.async_listen(driver_ready)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOGGER.info(f"KeyboardInterrupt")
    except SystemExit:
        _LOGGER.info(f"SystemExit")
    except Exception as e:
        _LOGGER.error(e)
    finally:
        container = docker_client.containers.get(CONTAINER_ID)
        container.stop()
        container.remove()


