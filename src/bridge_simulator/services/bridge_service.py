from bridge_simulator.blocking_queue import BlockingQueue


class BridgeService:
    def __init__(self, capacity: int) -> None:
        # The queue contains cars currently on the bridge.
        self.bridge = BlockingQueue(capacity)

    def enter(self, car) -> None:
        """
        Adds a car to the bridge.

        Blocks if the bridge is currently at capacity.
        """
        self.bridge.add(car)

    def exit(self):
        """
        Removes and returns the first car from the bridge.

        Blocks if the bridge is empty.
        """
        return self.bridge.remove()

    def get_status(self) -> dict:
        """
        Returns the current bridge state.
        """
        return {
            "cars_on_bridge": self.bridge.size(),
            "capacity": self.bridge.capacity,
        }