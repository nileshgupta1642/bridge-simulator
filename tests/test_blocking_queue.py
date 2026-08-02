import asyncio

from bridge_simulator.blocking_queue import BlockingQueue


def test_adds_and_removes_car_from_bridge() -> None:
    async def scenario() -> None:
        bridge = BlockingQueue(capacity=2)

        await bridge.add("car-1")

        assert await bridge.size() == 1
        assert await bridge.remove() == "car-1"
        assert await bridge.size() == 0

    asyncio.run(scenario())


def test_cars_exit_in_the_order_they_entered() -> None:
    async def scenario() -> None:
        bridge = BlockingQueue(capacity=3)

        await bridge.add("car-1")
        await bridge.add("car-2")
        await bridge.add("car-3")

        assert await bridge.remove() == "car-1"
        assert await bridge.remove() == "car-2"
        assert await bridge.remove() == "car-3"

        assert await bridge.size() == 0

    asyncio.run(scenario())


def test_remove_waits_when_bridge_is_empty() -> None:
    async def scenario() -> None:
        bridge = BlockingQueue(capacity=1)

        remove_task = asyncio.create_task(bridge.remove())
        await asyncio.sleep(0.1)

        assert remove_task.done() is False

        await bridge.add("car-1")

        assert await asyncio.wait_for(remove_task, timeout=1) == "car-1"
        assert await bridge.size() == 0

    asyncio.run(scenario())


def test_add_waits_when_bridge_is_at_capacity() -> None:
    async def scenario() -> None:
        bridge = BlockingQueue(capacity=1)

        await bridge.add("car-1")

        add_task = asyncio.create_task(bridge.add("car-2"))
        await asyncio.sleep(0.1)

        assert add_task.done() is False
        assert await bridge.size() == 1

        assert await bridge.remove() == "car-1"

        await asyncio.wait_for(add_task, timeout=1)

        assert await bridge.size() == 1
        assert await bridge.remove() == "car-2"

    asyncio.run(scenario())


def test_bridge_never_exceeds_capacity() -> None:
    async def scenario() -> None:
        bridge = BlockingQueue(capacity=2)

        await bridge.add("car-1")
        await bridge.add("car-2")

        third_car_task = asyncio.create_task(bridge.add("car-3"))
        await asyncio.sleep(0.1)

        assert third_car_task.done() is False
        assert await bridge.size() == 2

        await bridge.remove()
        await asyncio.wait_for(third_car_task, timeout=1)

        assert await bridge.size() == 2

    asyncio.run(scenario())
