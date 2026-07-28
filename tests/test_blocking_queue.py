from threading import Event, Thread

from bridge_simulator.blocking_queue import BlockingQueue


def test_add_and_remove_car() -> None:
    queue = BlockingQueue(capacity=2)

    queue.add("car-1")

    assert queue.size() == 1
    assert queue.remove() == "car-1"
    assert queue.size() == 0


def test_cars_are_removed_in_fifo_order() -> None:
    queue = BlockingQueue(capacity=3)

    queue.add("car-1")
    queue.add("car-2")
    queue.add("car-3")

    assert queue.remove() == "car-1"
    assert queue.remove() == "car-2"
    assert queue.remove() == "car-3"


def test_remove_blocks_when_queue_is_empty() -> None:
    queue = BlockingQueue(capacity=1)

    removed_car = []
    remove_finished = Event()

    def remove_car() -> None:
        car = queue.remove()
        removed_car.append(car)
        remove_finished.set()

    thread = Thread(target=remove_car, daemon=True)
    thread.start()

    # remove() should still be blocked because the queue is empty.
    assert remove_finished.wait(timeout=0.1) is False

    queue.add("car-1")

    # Adding a car should unblock remove().
    assert remove_finished.wait(timeout=1) is True

    thread.join(timeout=1)

    assert thread.is_alive() is False
    assert removed_car == ["car-1"]
    assert queue.size() == 0


def test_add_blocks_when_queue_is_full() -> None:
    queue = BlockingQueue(capacity=1)

    queue.add("car-1")

    add_finished = Event()

    def add_car() -> None:
        queue.add("car-2")
        add_finished.set()

    thread = Thread(target=add_car, daemon=True)
    thread.start()

    # add() should still be blocked because the queue is full.
    assert add_finished.wait(timeout=0.1) is False
    assert queue.size() == 1

    assert queue.remove() == "car-1"

    # Removing car-1 creates space and should unblock add().
    assert add_finished.wait(timeout=1) is True

    thread.join(timeout=1)

    assert thread.is_alive() is False
    assert queue.size() == 1
    assert queue.remove() == "car-2"