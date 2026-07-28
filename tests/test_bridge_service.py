from threading import Event, Thread

from bridge_simulator.services.bridge_service import BridgeService


def test_car_can_enter_bridge() -> None:
    service = BridgeService(capacity=2)

    service.enter("car-1")

    assert service.get_status() == {
        "cars_on_bridge": 1,
        "capacity": 2,
    }


def test_car_can_exit_bridge() -> None:
    service = BridgeService(capacity=2)

    service.enter("car-1")

    exited_car = service.exit()

    assert exited_car == "car-1"
    assert service.get_status() == {
        "cars_on_bridge": 0,
        "capacity": 2,
    }


def test_cars_exit_in_the_order_they_entered() -> None:
    service = BridgeService(capacity=3)

    service.enter("car-1")
    service.enter("car-2")
    service.enter("car-3")

    assert service.exit() == "car-1"
    assert service.exit() == "car-2"
    assert service.exit() == "car-3"


def test_enter_blocks_when_bridge_is_at_capacity() -> None:
    service = BridgeService(capacity=1)

    service.enter("car-1")

    second_car_entered = Event()

    def enter_second_car() -> None:
        service.enter("car-2")
        second_car_entered.set()

    thread = Thread(target=enter_second_car)
    thread.start()

    # car-2 should be blocked because car-1 occupies the bridge.
    assert second_car_entered.wait(timeout=0.1) is False

    exited_car = service.exit()

    assert exited_car == "car-1"

    # Once car-1 exits, car-2 should be admitted.
    assert second_car_entered.wait(timeout=1) is True

    thread.join(timeout=1)

    assert thread.is_alive() is False
    assert service.get_status() == {
        "cars_on_bridge": 1,
        "capacity": 1,
    }

    assert service.exit() == "car-2"