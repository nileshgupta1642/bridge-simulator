from threading import Event, Thread

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


def test_enter_blocks_when_bridge_is_at_capacity() -> None:
    service = BridgeService(capacity=1)
    app = create_app(service)

    with TestClient(app) as client:
        first_response = client.post(
            "/bridge/enter",
            json={"car_id": "car-1"},
        )

        assert first_response.status_code == 200

        second_request_finished = Event()
        second_responses = []

        def enter_second_car() -> None:
            with TestClient(app) as second_client:
                response = second_client.post(
                    "/bridge/enter",
                    json={"car_id": "car-2"},
                )

            second_responses.append(response)
            second_request_finished.set()

        thread = Thread(
            target=enter_second_car,
            daemon=True,
        )
        thread.start()

        # car-2 should be blocked because car-1 is on the bridge.
        assert second_request_finished.wait(timeout=0.1) is False

        status_response = client.get("/bridge/status")

        assert status_response.json() == {
            "cars_on_bridge": 1,
            "capacity": 1,
        }

        exit_response = client.post("/bridge/exit")

        assert exit_response.json() == {
            "car_id": "car-1",
            "status": "exited",
        }

        # car-1 exiting should allow car-2 to enter.
        assert second_request_finished.wait(timeout=1) is True

        thread.join(timeout=1)

        assert thread.is_alive() is False
        assert len(second_responses) == 1
        assert second_responses[0].status_code == 200
        assert second_responses[0].json() == {
            "car_id": "car-2",
            "status": "entered",
        }

        assert client.get("/bridge/status").json() == {
            "cars_on_bridge": 1,
            "capacity": 1,
        }

        # Clean up the remaining car.
        client.post("/bridge/exit")


def test_enter_requires_car_id() -> None:
    service = BridgeService(capacity=3)
    app = create_app(service)

    with TestClient(app) as client:
        response = client.post(
            "/bridge/enter",
            json={},
        )

    assert response.status_code == 422