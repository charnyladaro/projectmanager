document.addEventListener("DOMContentLoaded", () => {
  const updateRunningTimers = () => {
    document.querySelectorAll(".task-item").forEach((taskItem) => {
      const taskId = taskItem.id.split("-")[1];
      const runningTimerElem = document.getElementById(
        `running-timer-${taskId}`
      );
      const holdTimeElem = document.getElementById(`hold-time-${taskId}`);
      const startButton = taskItem.querySelector(
        `.start-timer[data-task-id="${taskId}"]`
      );
      const holdButton = taskItem.querySelector(
        `.hold-timer[data-task-id="${taskId}"]`
      );

      if (startButton.dataset.timerRunning === "true") {
        const startTime = new Date(startButton.dataset.startTime);
        const elapsedTime = Math.round((new Date() - startTime) / 1000);
        runningTimerElem.textContent = formatTime(elapsedTime);
      } else {
        runningTimerElem.textContent = "00:00:00";
      }

      if (holdButton.dataset.timerHold === "true") {
        const holdTime = parseInt(holdButton.dataset.holdTime);
        holdTimeElem.textContent = formatTime(holdTime);
      }
    });
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
      .toString()
      .padStart(2, "0");
    const minutes = Math.floor((seconds % 3600) / 60)
      .toString()
      .padStart(2, "0");
    const secs = (seconds % 60).toString().padStart(2, "0");
    return `${hours}:${minutes}:${secs}`;
  };

  setInterval(updateRunningTimers, 1000);

  document.querySelectorAll(".start-timer").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const taskId = button.dataset.taskId;
      const startTime = new Date();
      button.dataset.timerRunning = "true";
      button.dataset.startTime = startTime.toISOString();
      fetch(`/start_timer/${taskId}`, { method: "POST" })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "timer started") {
            console.log(`Timer started for task ${taskId}`);
            button.style.display = "none";
            const holdButton = document.querySelector(
              `.hold-timer[data-task-id="${taskId}"]`
            );
            holdButton.style.display = "inline-block";
          }
        });
    });
  });

  document.querySelectorAll(".stop-timer").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const taskId = button.dataset.taskId;
      const startButton = document.querySelector(
        `.start-timer[data-task-id="${taskId}"]`
      );
      const startTime = new Date(startButton.dataset.startTime);
      const elapsedTime = Math.round((new Date() - startTime) / 1000);
      fetch(`/stop_timer/${taskId}`, { method: "POST" })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "timer stopped") {
            console.log(`Timer stopped for task ${taskId}`);
            startButton.dataset.timerRunning = "false";
            document.getElementById(`running-timer-${taskId}`).textContent =
              "00:00:00";
            const timeSpentElem = document.getElementById(
              `time-spent-${taskId}`
            );
            timeSpentElem.textContent = formatTime(
              parseInt(timeSpentElem.textContent) + elapsedTime
            );
            startButton.style.display = "inline-block";
            const holdButton = document.querySelector(
              `.hold-timer[data-task-id="${taskId}"]`
            );
            holdButton.style.display = "none";
          }
        });
    });
  });

  document.querySelectorAll(".hold-timer").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const taskId = button.dataset.taskId;
      const startButton = document.querySelector(
        `.start-timer[data-task-id="${taskId}"]`
      );
      const holdButton = document.querySelector(
        `.hold-timer[data-task-id="${taskId}"]`
      );
      const holdTimeElem = document.getElementById(`hold-time-${taskId}`);

      if (button.dataset.timerHold === "false") {
        button.dataset.timerHold = "true";
        button.dataset.holdStart = new Date().toISOString();
        startButton.dataset.timerRunning = "false";
        fetch(`/hold_timer/${taskId}`, { method: "POST" })
          .then((response) => response.json())
          .then((data) => {
            if (data.status === "timer held") {
              console.log(`Timer held for task ${taskId}`);
              button.textContent = "Resume Timer";
              startButton.style.display = "none";
            }
          });
      } else {
        const holdStart = new Date(button.dataset.holdStart);
        const holdTime = Math.round((new Date() - holdStart) / 1000);
        button.dataset.timerHold = "false";
        button.dataset.holdTime = holdTime;
        holdTimeElem.textContent = formatTime(holdTime);
        startButton.dataset.timerRunning = "true"; // Resume the running timer
        button.textContent = "Hold Timer";
        startButton.style.display = "none";
      }
    });
  });
});
