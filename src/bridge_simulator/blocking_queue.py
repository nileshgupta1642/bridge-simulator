import asyncio


class SimulationRestarted(Exception):
    """Raised when a pending bridge operation belongs to an old simulation."""


class BlockingQueue: 
    def __init__(self, capacity) -> None: 
        self.capacity = capacity
        self.cars = []
        self.lock = asyncio.Lock()
        self.closed = asyncio.Event()

        self.cars_available = asyncio.Semaphore(0) # Originally no cars, so start 0
        self.spaces_available = asyncio.Semaphore(capacity) # Number of available spaces on the bridge

    async def _acquire_unless_closed(
        self,
        semaphore: asyncio.Semaphore,
    ) -> None:
        if self.closed.is_set():
            raise SimulationRestarted

        acquire_task = asyncio.create_task(semaphore.acquire())
        closed_task = asyncio.create_task(self.closed.wait())
        tasks = (acquire_task, closed_task)

        try:
            done, _ = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if closed_task in done:
                raise SimulationRestarted
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)

    def close(self) -> None:
        """Stops pending operations that belong to this queue."""
        self.closed.set()

    async def add(self, car) -> None:
        '''
        Adds a car to the bridge

        1. Ensures that we aren't at the max already, blocks if so
        2. With a lock, updates the queue
        3. Updates cars available  
        '''
        # Block if no space on bridge
        await self._acquire_unless_closed(self.spaces_available)

        # Add to cars on bridge
        async with self.lock:
            if self.closed.is_set():
                raise SimulationRestarted

            self.cars.append(car)

        # Signal another car is on the bridge
        self.cars_available.release() 

    async def remove(self):
        '''
        Removes car from the bridge

        1. Ensures we can remove it and blocks if empty
        2. With lock, updates the queue
        3. Signals that we have space available
        '''
        # Blocks when no cars on bridge
        await self._acquire_unless_closed(self.cars_available)

        async with self.lock:
            if self.closed.is_set():
                raise SimulationRestarted

            car = self.cars.pop(0)

        # Signals space is available on the bridge
        self.spaces_available.release()

        return car

    async def size(self) -> int:
        '''
        Returns the number of cars currently on the bridge
        '''
        async with self.lock:
            return len(self.cars)
