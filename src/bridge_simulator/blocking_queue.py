from threading import Lock, Semaphore

class BlockingQueue: 
    def __init__(self, capacity) -> None: 
        self.capacity = capacity
        self.cars = []
        self.lock = Lock() 

        self.cars_available = Semaphore(0) # Originally no cars, so start 0
        self.spaces_available = Semaphore(capacity) # Max number of cars allowed on bridge

    def add(self, car) -> None:
        '''
        Adds the car to back of the waiting queue 

        1. Ensures that we aren't at the max already, blocks if so
        2. With a lock, updates the queue
        3. Updates cars available  
        '''
        # Ensure we aren't at max already 
        self.spaces_available.acquire() 

        # Append to queue
        with self.lock: 
            self.cars.append(car)

        # Signal another car is available
        self.cars_available.release() 

    def remove(self): 
        '''
        Removes car from the waiting queue 

        1. Ensures we can remove it and blocks if empty
        2. With lock, updates the queue
        3. Signals that we have space available
        '''
        # Blocks when no cars
        self.cars_available.acquire()

        with self.lock: 
            car = self.cars.pop(0)

        # Signals space is available 
        self.spaces_available.release()

        return car

    def size(self) -> int: 
        '''
        Returns the number of cars waiting in the queue 
        '''
        with self.lock: 
            return len(self.cars)

