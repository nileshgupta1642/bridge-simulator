from bridge_simulator.blocking_queue import BlockingQueue


class BridgeService:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        # The queue contains cars currently on the bridge.
        self.bridge = BlockingQueue(capacity)

    async def enter(self, car) -> None:
        """
        Adds a car to the bridge.

        Blocks if the bridge is currently at capacity.
        """
        await self.bridge.add(car)

    async def exit(self):
        """
        Removes and returns the first car from the bridge.

        Blocks if the bridge is empty.
        """
        return await self.bridge.remove()

    async def get_status(self) -> dict:
        """
        Returns the current bridge state.
        """
        return {
            "cars_on_bridge": await self.bridge.size(),
            "capacity": self.bridge.capacity,
        }

    async def restart(self) -> None:
        """Clears the bridge and starts a new simulation."""
        old_bridge = self.bridge
        self.bridge = BlockingQueue(self.capacity)
        old_bridge.close()
