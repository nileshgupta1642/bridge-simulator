from threading import Lock, Semaphore

class BlockingQueue: 
    def __init__(self, capacity) -> None: 
        self.capacity = capacity
        self.cars = []
        self.lock = Lock() 

        self.cars_available = Semaphore(0) # Originally no cars, so start 0
        self.spaces_available = Semaphore(capacity) # Number of available spaces on the bridge

    def add(self, car) -> None:
        '''
        Adds a car to the bridge

        1. Ensures that we aren't at the max already, blocks if so
        2. With a lock, updates the queue
        3. Updates cars available  
        '''
        # Block if no space on bridge
        self.spaces_available.acquire() 

        # Add to cars on bridge
        with self.lock: 
            self.cars.append(car)

        # Signal another car is on the bridge
        self.cars_available.release() 

    def remove(self): 
        '''
        Removes car from the bridge

        1. Ensures we can remove it and blocks if empty
        2. With lock, updates the queue
        3. Signals that we have space available
        '''
        # Blocks when no cars on bridge
        self.cars_available.acquire()

        with self.lock: 
            car = self.cars.pop(0)

        # Signals space is available on the bridge
        self.spaces_available.release()

        return car

    def size(self) -> int: 
        '''
        Returns the number of cars currently on the bridge
        '''
        with self.lock: 
            return len(self.cars)

