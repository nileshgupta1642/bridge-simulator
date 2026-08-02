from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bridge_simulator.blocking_queue import SimulationRestarted
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

    @app.exception_handler(SimulationRestarted)
    async def simulation_restarted(
        request: Request,
        exception: SimulationRestarted,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": "Simulation restarted"},
        )

    @app.post("/bridge/enter")
    async def enter_bridge(request: EnterBridgeRequest) -> dict:
        # Waits without occupying a worker if the bridge is at capacity.
        await service.enter(request.car_id)

        return {
            "car_id": request.car_id,
            "status": "entered",
        }

    @app.post("/bridge/exit")
    async def exit_bridge() -> dict:
        # Waits without occupying a worker if there are no cars on the bridge.
        car_id = await service.exit()

        return {
            "car_id": car_id,
            "status": "exited",
        }

    @app.get("/bridge/status")
    async def get_bridge_status() -> dict:
        return await service.get_status()

    @app.post("/bridge/restart")
    async def restart_bridge() -> dict:
        await service.restart()

        return {"status": "restarted"}

    return app


app = create_app()
