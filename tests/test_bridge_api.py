import asyncio

import httpx
from fastapi.testclient import TestClient

from bridge_simulator.api.bridge_api import create_app
from bridge_simulator.services.bridge_service import BridgeService


def test_initial_bridge_status() -> None:
    service = BridgeService(capacity=3)
    app = create_app(service)

    with TestClient(app) as client:
        response = client.get("/bridge/status")

    assert response.status_code == 200
    assert response.json() == {
        "cars_on_bridge": 0,
        "capacity": 3,
    }


def test_car_can_enter_bridge() -> None:
    service = BridgeService(capacity=3)
    app = create_app(service)

    with TestClient(app) as client:
        response = client.post(
            "/bridge/enter",
            json={"car_id": "car-1"},
        )

        status_response = client.get("/bridge/status")

    assert response.status_code == 200
    assert response.json() == {
        "car_id": "car-1",
        "status": "entered",
    }

    assert status_response.status_code == 200
    assert status_response.json() == {
        "cars_on_bridge": 1,
        "capacity": 3,
    }


def test_car_can_exit_bridge() -> None:
    service = BridgeService(capacity=3)
    app = create_app(service)

    with TestClient(app) as client:
        client.post(
            "/bridge/enter",
            json={"car_id": "car-1"},
        )

        response = client.post("/bridge/exit")
        status_response = client.get("/bridge/status")

    assert response.status_code == 200
    assert response.json() == {
        "car_id": "car-1",
        "status": "exited",
    }

    assert status_response.status_code == 200
    assert status_response.json() == {
        "cars_on_bridge": 0,
        "capacity": 3,
    }


def test_cars_exit_in_fifo_order() -> None:
    service = BridgeService(capacity=3)
    app = create_app(service)

    with TestClient(app) as client:
        client.post(
            "/bridge/enter",
            json={"car_id": "car-1"},
        )
        client.post(
            "/bridge/enter",
            json={"car_id": "car-2"},
        )
        client.post(
            "/bridge/enter",
            json={"car_id": "car-3"},
        )

        first_exit = client.post("/bridge/exit")
        second_exit = client.post("/bridge/exit")
        third_exit = client.post("/bridge/exit")

    assert first_exit.json() == {
        "car_id": "car-1",
        "status": "exited",
    }
    assert second_exit.json() == {
        "car_id": "car-2",
        "status": "exited",
    }
    assert third_exit.json() == {
        "car_id": "car-3",
        "status": "exited",
    }


def test_enter_waits_when_bridge_is_at_capacity() -> None:
    async def scenario() -> None:
        service = BridgeService(capacity=1)
        app = create_app(service)
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            first_response = await client.post(
                "/bridge/enter",
                json={"car_id": "car-1"},
            )

            assert first_response.status_code == 200

            second_request = asyncio.create_task(
                client.post(
                    "/bridge/enter",
                    json={"car_id": "car-2"},
                )
            )
            await asyncio.sleep(0.1)

            assert second_request.done() is False

            status_response = await client.get("/bridge/status")

            assert status_response.json() == {
                "cars_on_bridge": 1,
                "capacity": 1,
            }

            exit_response = await client.post("/bridge/exit")

            assert exit_response.json() == {
                "car_id": "car-1",
                "status": "exited",
            }

            second_response = await asyncio.wait_for(
                second_request,
                timeout=1,
            )

            assert second_response.status_code == 200
            assert second_response.json() == {
                "car_id": "car-2",
                "status": "entered",
            }

            assert (await client.get("/bridge/status")).json() == {
                "cars_on_bridge": 1,
                "capacity": 1,
            }

            await client.post("/bridge/exit")

    asyncio.run(scenario())


def test_exit_responds_with_many_enter_requests_waiting() -> None:
    async def scenario() -> None:
        service = BridgeService(capacity=1)
        app = create_app(service)
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            await client.post(
                "/bridge/enter",
                json={"car_id": "car-on-bridge"},
            )

            waiting_requests = [
                asyncio.create_task(
                    client.post(
                        "/bridge/enter",
                        json={"car_id": f"waiting-{index}"},
                    )
                )
                for index in range(50)
            ]
            await asyncio.sleep(0.1)

            assert all(
                request.done() is False
                for request in waiting_requests
            )

            exit_response = await asyncio.wait_for(
                client.post("/bridge/exit"),
                timeout=1,
            )

            assert exit_response.json() == {
                "car_id": "car-on-bridge",
                "status": "exited",
            }

            # Each exit admits the next waiting request. Drain every car so
            # the test leaves no pending tasks behind.
            for _ in waiting_requests:
                await client.post("/bridge/exit")

            responses = await asyncio.gather(*waiting_requests)

            assert all(response.status_code == 200 for response in responses)
            assert (await client.get("/bridge/status")).json() == {
                "cars_on_bridge": 0,
                "capacity": 1,
            }

    asyncio.run(scenario())


def test_restart_clears_bridge_and_releases_waiting_enter() -> None:
    async def scenario() -> None:
        service = BridgeService(capacity=1)
        app = create_app(service)
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            await client.post(
                "/bridge/enter",
                json={"car_id": "car-on-bridge"},
            )
            waiting_enter = asyncio.create_task(
                client.post(
                    "/bridge/enter",
                    json={"car_id": "waiting-car"},
                )
            )
            await asyncio.sleep(0.1)

            assert waiting_enter.done() is False

            restart_response = await client.post("/bridge/restart")

            assert restart_response.status_code == 200
            assert restart_response.json() == {"status": "restarted"}

            waiting_response = await asyncio.wait_for(
                waiting_enter,
                timeout=1,
            )

            assert waiting_response.status_code == 409
            assert waiting_response.json() == {
                "detail": "Simulation restarted",
            }
            assert (await client.get("/bridge/status")).json() == {
                "cars_on_bridge": 0,
                "capacity": 1,
            }

            new_enter = await client.post(
                "/bridge/enter",
                json={"car_id": "new-car"},
            )

            assert new_enter.status_code == 200
            assert (await client.post("/bridge/exit")).json() == {
                "car_id": "new-car",
                "status": "exited",
            }

    asyncio.run(scenario())


def test_restart_releases_waiting_exit() -> None:
    async def scenario() -> None:
        service = BridgeService(capacity=1)
        app = create_app(service)
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            waiting_exit = asyncio.create_task(
                client.post("/bridge/exit")
            )
            await asyncio.sleep(0.1)

            assert waiting_exit.done() is False

            await client.post("/bridge/restart")

            waiting_response = await asyncio.wait_for(
                waiting_exit,
                timeout=1,
            )

            assert waiting_response.status_code == 409
            assert waiting_response.json() == {
                "detail": "Simulation restarted",
            }

    asyncio.run(scenario())


def test_enter_requires_car_id() -> None:
    service = BridgeService(capacity=3)
    app = create_app(service)

    with TestClient(app) as client:
        response = client.post(
            "/bridge/enter",
            json={},
        )

    assert response.status_code == 422
