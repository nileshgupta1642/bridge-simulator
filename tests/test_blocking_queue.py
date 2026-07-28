from threading import Event, Thread

from bridge_simulator.blocking_queue import BlockingQueue


def test_adds_and_removes_car_from_bridge() -> None:
    bridge = BlockingQueue(capacity=2)

    bridge.add("car-1")

    assert bridge.size() == 1
    assert bridge.remove() == "car-1"
    assert bridge.size() == 0


def test_cars_exit_in_the_order_they_entered() -> None:
    bridge = BlockingQueue(capacity=3)

    bridge.add("car-1")
    bridge.add("car-2")
    bridge.add("car-3")

    assert bridge.remove() == "car-1"
    assert bridge.remove() == "car-2"
    assert bridge.remove() == "car-3"

    assert bridge.size() == 0


def test_remove_blocks_when_bridge_is_empty() -> None:
    bridge = BlockingQueue(capacity=1)

    removed_cars = []
    remove_finished = Event()

    def remove_car() -> None:
        car = bridge.remove()
        removed_cars.append(car)
        remove_finished.set()

    thread = Thread(target=remove_car)
    thread.start()

    # The bridge is empty, so remove() should remain blocked.
    assert remove_finished.wait(timeout=0.1) is False

    bridge.add("car-1")

    # Adding a car should allow remove() to continue.
    assert remove_finished.wait(timeout=1) is True

    thread.join(timeout=1)

    assert thread.is_alive() is False
    assert removed_cars == ["car-1"]
    assert bridge.size() == 0


def test_add_blocks_when_bridge_is_at_capacity() -> None:
    bridge = BlockingQueue(capacity=1)

    bridge.add("car-1")

    add_finished = Event()

    def add_second_car() -> None:
        bridge.add("car-2")
        add_finished.set()

    thread = Thread(target=add_second_car)
    thread.start()

    # The bridge is full, so car-2 should remain blocked at the entrance.
    assert add_finished.wait(timeout=0.1) is False
    assert bridge.size() == 1

    assert bridge.remove() == "car-1"

    # Removing car-1 creates a bridge space for car-2.
    assert add_finished.wait(timeout=1) is True

    thread.join(timeout=1)

    assert thread.is_alive() is False
    assert bridge.size() == 1
    assert bridge.remove() == "car-2"


def test_bridge_never_exceeds_capacity() -> None:
    bridge = BlockingQueue(capacity=2)

    bridge.add("car-1")
    bridge.add("car-2")

    third_car_entered = Event()

    def add_third_car() -> None:
        bridge.add("car-3")
        third_car_entered.set()

    thread = Thread(target=add_third_car)
    thread.start()

    assert third_car_entered.wait(timeout=0.1) is False
    assert bridge.size() == 2

    bridge.remove()

    assert third_car_entered.wait(timeout=1) is True

    thread.join(timeout=1)

    assert thread.is_alive() is False
    assert bridge.size() == 2