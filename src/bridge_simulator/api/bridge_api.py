from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bridge_simulator.services.bridge_service import BridgeService


class EnterBridgeRequest(BaseModel):
    car_id: str


def create_app(
    bridge_service: BridgeService | None = None,
) -> FastAPI:
    app = FastAPI()

    service = (
        bridge_service
        if bridge_service is not None
        else BridgeService(capacity=3)
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/bridge/enter")
    def enter_bridge(request: EnterBridgeRequest) -> dict:
        # Blocks here if the bridge is currently at capacity.
        service.enter(request.car_id)

        return {
            "car_id": request.car_id,
            "status": "entered",
        }

    @app.post("/bridge/exit")
    def exit_bridge() -> dict:
        # Blocks here if there are no cars on the bridge.
        car_id = service.exit()

        return {
            "car_id": car_id,
            "status": "exited",
        }

    @app.get("/bridge/status")
    def get_bridge_status() -> dict:
        return service.get_status()

    return app


app = create_app()