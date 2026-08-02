import asyncio

import pytest

from bridge_simulator.blocking_queue import SimulationRestarted
from bridge_simulator.services.bridge_service import BridgeService


def test_car_can_enter_bridge() -> None:
    async def scenario() -> None:
        service = BridgeService(capacity=2)

        await service.enter("car-1")

        assert await service.get_status() == {
            "cars_on_bridge": 1,
            "capacity": 2,
        }

    asyncio.run(scenario())


def test_car_can_exit_bridge() -> None:
    async def scenario() -> None:
        service = BridgeService(capacity=2)

        await service.enter("car-1")

        exited_car = await service.exit()

        assert exited_car == "car-1"
        assert await service.get_status() == {
            "cars_on_bridge": 0,
            "capacity": 2,
        }

    asyncio.run(scenario())


def test_cars_exit_in_the_order_they_entered() -> None:
    async def scenario() -> None:
        service = BridgeService(capacity=3)

        await service.enter("car-1")
        await service.enter("car-2")
        await service.enter("car-3")

        assert await service.exit() == "car-1"
        assert await service.exit() == "car-2"
        assert await service.exit() == "car-3"

    asyncio.run(scenario())


def test_enter_waits_when_bridge_is_at_capacity() -> None:
    async def scenario() -> None:
        service = BridgeService(capacity=1)

        await service.enter("car-1")

        second_car_task = asyncio.create_task(service.enter("car-2"))
        await asyncio.sleep(0.1)

        assert second_car_task.done() is False

        exited_car = await service.exit()

        assert exited_car == "car-1"

        await asyncio.wait_for(second_car_task, timeout=1)

        assert await service.get_status() == {
            "cars_on_bridge": 1,
            "capacity": 1,
        }

        assert await service.exit() == "car-2"

    asyncio.run(scenario())


def test_restart_clears_bridge_and_closes_old_requests() -> None:
    async def scenario() -> None:
        service = BridgeService(capacity=1)

        await service.enter("car-1")
        waiting_enter = asyncio.create_task(service.enter("car-2"))
        await asyncio.sleep(0.1)

        await service.restart()

        with pytest.raises(SimulationRestarted):
            await asyncio.wait_for(waiting_enter, timeout=1)

        assert await service.get_status() == {
            "cars_on_bridge": 0,
            "capacity": 1,
        }

    asyncio.run(scenario())
