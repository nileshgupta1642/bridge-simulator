const API_URL = "http://localhost:8001";

const SPAWN_INTERVAL_MS = 5_000;
const APPROACH_DURATION_MS = 3_000;
const BRIDGE_CROSSING_DURATION_MS = 15_000;
const LEAVING_DURATION_MS = 3_000;
const QUEUE_ADVANCE_DURATION_MS = 750;
const CAR_GAP_PX = 24;

const CAR_COLORS = [
  "#d94841",
  "#2471a3",
  "#7d3c98",
  "#d68910",
  "#1e8449",
  "#ca6f1e",
  "#2e86c1",
  "#884ea0",
];

const scene = document.querySelector("#scene");
const carsContainer = document.querySelector("#cars");
const entranceSign = document.querySelector("#bridge-entrance");
const exitSign = document.querySelector("#bridge-exit");

let nextCarId = 1;
let previousColorIndex = -1;
const entranceQueue = [];

async function restartSimulation() {
  const response = await fetch(`${API_URL}/bridge/restart`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(
      `Could not restart simulation: ${response.status}`
    );
  }

  return response.json();
}

async function enterBridge(carId) {
  const response = await fetch(`${API_URL}/bridge/enter`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      car_id: carId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Could not enter bridge: ${response.status}`);
  }

  return response.json();
}

async function exitBridge(carId) {
  const response = await fetch(`${API_URL}/bridge/exit`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Could not exit bridge: ${response.status}`);
  }

  const result = await response.json();

  if (result.car_id !== carId) {
    console.warn(
      `Expected ${carId} to exit, but backend removed ${result.car_id}`
    );
  }

  return result;
}

function moveCar(car, destinationX, durationMs) {
  return new Promise((resolve) => {
    function handleTransitionEnd(event) {
      if (event.propertyName !== "left") {
        return;
      }

      car.removeEventListener(
        "transitionend",
        handleTransitionEnd
      );

      resolve();
    }

    car.addEventListener(
      "transitionend",
      handleTransitionEnd
    );

    car.style.transitionDuration = `${durationMs}ms`;

    requestAnimationFrame(() => {
      car.style.left = `${destinationX}px`;
    });
  });
}

function getCheckpointPositions(car) {
  const sceneRect = scene.getBoundingClientRect();
  const entranceRect = entranceSign.getBoundingClientRect();
  const exitRect = exitSign.getBoundingClientRect();

  const entrancePoint =
    entranceRect.left +
    entranceRect.width / 2 -
    sceneRect.left;

  const exitPoint =
    exitRect.left +
    exitRect.width / 2 -
    sceneRect.left;

  return {
    // Stop when the front of the car reaches the entrance.
    entrance: entrancePoint - car.offsetWidth,

    // Stop when the entire car has cleared the bridge.
    exit: exitPoint,

    // Move completely off the screen.
    offscreen: scene.clientWidth + car.offsetWidth,
  };
}

function getEntranceQueuePosition(entry, index) {
  const spacing = entry.car.offsetWidth + CAR_GAP_PX;
  return entry.positions.entrance - index * spacing;
}

function scheduleQueueMove(entry, index, durationMs) {
  const destination = getEntranceQueuePosition(entry, index);

  entry.movement = entry.movement.then(() =>
    moveCar(entry.car, destination, durationMs)
  );
}

function getBridgeEntryDelay(entry) {
  const bridgeDistance = Math.max(
    1,
    entry.positions.exit - entry.positions.entrance
  );
  const desiredSpacing = entry.car.offsetWidth + CAR_GAP_PX;

  return Math.ceil(
    BRIDGE_CROSSING_DURATION_MS *
      (desiredSpacing / bridgeDistance)
  );
}

function advanceEntranceQueue(delayMs) {
  const movementDuration = Math.max(
    QUEUE_ADVANCE_DURATION_MS,
    delayMs
  );

  entranceQueue.forEach((entry, index) => {
    scheduleQueueMove(
      entry,
      index,
      movementDuration
    );
  });

  const nextEntry = entranceQueue[0];

  if (nextEntry) {
    setTimeout(nextEntry.allowEntry, delayMs);
  }
}

async function waitForBridgeAdmission(car, carId, positions) {
  let resolveTurn;

  const turn = new Promise((resolve) => {
    resolveTurn = resolve;
  });

  const entry = {
    car,
    carId,
    positions,
    movement: Promise.resolve(),
    allowEntry: resolveTurn,
  };

  entranceQueue.push(entry);
  scheduleQueueMove(
    entry,
    entranceQueue.length - 1,
    APPROACH_DURATION_MS
  );

  if (entranceQueue[0] === entry) {
    entry.allowEntry();
  }

  await turn;
  await entry.movement;

  try {
    await enterBridge(carId);
  } catch (error) {
    entranceQueue.shift();
    advanceEntranceQueue(0);
    throw error;
  }

  entranceQueue.shift();
  advanceEntranceQueue(getBridgeEntryDelay(entry));
}

async function runCar(car, carId) {
  const positions = getCheckpointPositions(car);

  // Queue visibly behind the entrance, then wait for backend admission.
  await waitForBridgeAdmission(car, carId, positions);

  // The API responded, so this car is allowed to cross.
  await moveCar(
    car,
    positions.exit,
    BRIDGE_CROSSING_DURATION_MS
  );

  // Tell the backend that the car has left the bridge.
  await exitBridge(carId);

  // Continue moving off-screen.
  await moveCar(
    car,
    positions.offscreen,
    LEAVING_DURATION_MS
  );

  car.remove();
}

function createCar() {
  const carId = `car-${nextCarId}`;
  nextCarId += 1;

  const car = document.createElement("div");
  car.className = "car";
  car.dataset.carId = carId;

  let colorIndex;

  do {
    colorIndex = Math.floor(Math.random() * CAR_COLORS.length);
  } while (
    CAR_COLORS.length > 1 &&
    colorIndex === previousColorIndex
  );

  previousColorIndex = colorIndex;
  car.style.setProperty("--car-color", CAR_COLORS[colorIndex]);

  car.innerHTML = `
    <div class="car-roof"></div>
    <div class="car-window"></div>
    <div class="car-body"></div>
    <div class="wheel wheel-left"></div>
    <div class="wheel wheel-right"></div>
  `;

  carsContainer.appendChild(car);

  runCar(car, carId).catch((error) => {
    console.error(`${carId} stopped:`, error);
  });
}

async function initializeSimulation() {
  await restartSimulation();

  createCar();
  setInterval(createCar, SPAWN_INTERVAL_MS);
}

const restartButton = document.querySelector(
  "#restart-simulation"
);

restartButton.addEventListener("click", async () => {
  restartButton.disabled = true;

  try {
    await restartSimulation();
    window.location.reload();
  } catch (error) {
    restartButton.disabled = false;
    console.error("Could not restart simulation:", error);
  }
});

initializeSimulation().catch((error) => {
  console.error("Could not initialize simulation:", error);
});
