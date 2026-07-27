const SPAWN_INTERVAL_MS = 5_000;
const CROSSING_DURATION_MS = 8_000;

const scene = document.querySelector("#scene");
const carsContainer = document.querySelector("#cars");

function createCar() {
  const car = document.createElement("div");
  car.className = "car";

  car.innerHTML = `
    <div class="car-roof"></div>
    <div class="car-window"></div>
    <div class="car-body"></div>
    <div class="wheel wheel-left"></div>
    <div class="wheel wheel-right"></div>
  `;

  car.style.transitionDuration = `${CROSSING_DURATION_MS}ms`;

  carsContainer.appendChild(car);

  requestAnimationFrame(() => {
    car.style.left = `${scene.clientWidth + 90}px`;
  });

  car.addEventListener(
    "transitionend",
    () => {
      car.remove();
    },
    { once: true }
  );
}

createCar();
setInterval(createCar, SPAWN_INTERVAL_MS);