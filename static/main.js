let timers = {};
let projects = [];
let projectIdCounter = 0;
let taskIdCounter = 0;
let currentProjectId = null;

function startTimer(taskId) {
  if (!timers[taskId]) {
    timers[taskId] = { startTime: Date.now(), elapsedTime: 0, interval: null };
    timers[taskId].interval = setInterval(() => updateTimer(taskId), 1000);
  } else if (!timers[taskId].interval) {
    timers[taskId].startTime = Date.now() - timers[taskId].elapsedTime;
    timers[taskId].interval = setInterval(() => updateTimer(taskId), 1000);
  }

  moveTaskToBoard(taskId, "ongoing");
}

function pauseTimer(taskId) {
  if (timers[taskId] && timers[taskId].interval) {
    clearInterval(timers[taskId].interval);
    timers[taskId].elapsedTime = Date.now() - timers[taskId].startTime;
    timers[taskId].interval = null;

    moveTaskToBoard(taskId, "paused");
  }
}

function stopTimer(taskId) {
  if (timers[taskId]) {
    clearInterval(timers[taskId].interval);
    const totalElapsedTime = Math.floor(
      (Date.now() - timers[taskId].startTime) / 1000 / 60
    ); // Convert milliseconds to minutes
    const timeLoggedElement = document.getElementById(`time-logged-${taskId}`);
    const currentLoggedTime = parseInt(timeLoggedElement.textContent, 10);
    timeLoggedElement.textContent = currentLoggedTime + totalElapsedTime;

    // Clear timer display
    document.getElementById(`timer-display-${taskId}`).textContent = "";

    delete timers[taskId];

    moveTaskToBoard(taskId, "done");
  }
}

function updateTimer(taskId) {
  const elapsedTime = Math.floor(
    (Date.now() - timers[taskId].startTime) / 1000
  ); // Convert milliseconds to seconds
  const minutes = Math.floor(elapsedTime / 60);
  const seconds = elapsedTime % 60;
  document.getElementById(
    `timer-display-${taskId}`
  ).textContent = `Timer: ${minutes}m ${seconds}s`;
}

function allowDrop(ev) {
  ev.preventDefault();
}

function drag(ev) {
  ev.dataTransfer.setData("text", ev.target.id);
}

function drop(ev) {
  ev.preventDefault();
  const data = ev.dataTransfer.getData("text");
  const droppedElement = document.getElementById(data);
  if (ev.target.classList.contains("column")) {
    ev.target.appendChild(droppedElement);
  } else if (ev.target.classList.contains("task")) {
    ev.target.parentNode.insertBefore(droppedElement, ev.target.nextSibling);
  }
}

function addTaskToDOM(projectId, taskId, taskName, taskDescription) {
  const taskElement = document.createElement("div");
  taskElement.classList.add("task");
  taskElement.id = `task-${taskId}`;
  taskElement.draggable = true;
  taskElement.ondragstart = drag;

  taskElement.innerHTML = `
        <span>${taskName} - <span id="time-logged-${taskId}">0</span> minutes</span>
        <div class="timer-controls">
            <button class="btn timer-btn" onclick="startTimer(${taskId})">Start</button>
            <button class="btn timer-btn" onclick="pauseTimer(${taskId})">Pause</button>
            <button class="btn timer-btn" onclick="stopTimer(${taskId})">Stop</button>
        </div>
        <div class="timer-display" id="timer-display-${taskId}"></div>
    `;

  document
    .getElementById(`not-yet-started-${projectId}`)
    .appendChild(taskElement);
}

function addTask(projectId, taskName, taskDescription) {
  const taskId = taskIdCounter++; // Unique ID for the task
  addTaskToDOM(projectId, taskId, taskName, taskDescription);

  // Send AJAX request to save task to database
  fetch("/add_task", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      "task-name": taskName,
      "task-description": taskDescription,
      "project-id": projectId,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Task saved:", data);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

function addProjectToDOM(projectId, name, description) {
  const projectListItem = document.createElement("div");
  projectListItem.classList.add("project-list-item");
  projectListItem.id = `project-list-item-${projectId}`;
  projectListItem.onclick = () => displayProject(projectId);

  projectListItem.innerHTML = `
        <h3>${name}</h3>
         <button class="delete-btn" data-project-id="${projectId}">Delete Project</button>
    `;

  // Add an event listener for the delete button
  const deleteButton = projectListItem.querySelector(".delete-btn");
  deleteButton.addEventListener("click", (event) => {
    event.stopPropagation(); // Prevent click event from bubbling to projectListItem
    const projectIdToDelete = event.target.dataset.projectId;
    deleteProject(projectIdToDelete); // Call your delete function here
    // Optionally, remove the projectListItem from DOM after deletion
    projectListItem.remove();
  });

  document.getElementById("project-list").appendChild(projectListItem);

  if (currentProjectId === null) {
    displayProject(projectId);
  }
}

function addProject(name, description) {
  const projectId = projectIdCounter++; // Unique ID for the project
  projects.push({ id: projectId, name: name, description: description });

  addProjectToDOM(projectId, name, description);

  // Send AJAX request to save project to database
  fetch("/add_project", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      "project-name": name,
      "project-description": description,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Project saved:", data);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

function displayProject(projectId) {
  currentProjectId = projectId;

  const project = projects.find((proj) => proj.id === projectId);
  const currentProjectContainer = document.getElementById("current-project");
  currentProjectContainer.innerHTML = `
        <button id="add-task-btn" class="btn top-right-btn">Add Task</button>
        <h3>${project.name}</h3>
        <p>${project.description}</p>
        <div class="board">
            <div class="column" id="not-yet-started-${projectId}" ondrop="drop(event)" ondragover="allowDrop(event)">
                <h3>Not Yet Started</h3>
            </div>
            <div class="column" id="ongoing-${projectId}" ondrop="drop(event)" ondragover="allowDrop(event)">
                <h3>Ongoing</h3>
            </div>
            <div class="column" id="paused-${projectId}" ondrop="drop(event)" ondragover="allowDrop(event)">
                <h3>Paused Tasks</h3>
            </div>
            <div class="column" id="done-${projectId}" ondrop="drop(event)" ondragover="allowDrop(event)">
                <h3>Done</h3>
            </div>
        </div>
    `;

  // Add event listener for the newly created "Add Task" button
  document.getElementById("add-task-btn").onclick = () => {
    openModal("task-form-modal");
  };
}

function moveTaskToBoard(taskId, boardType) {
  const taskElement = document.getElementById(`task-${taskId}`);
  const projectId = currentProjectId;
  if (taskElement && projectId !== null) {
    const boardElement = document.getElementById(`${boardType}-${projectId}`);
    if (boardElement) {
      boardElement.appendChild(taskElement);
    }
  }
}

function handleTaskFormSubmit(event) {
  event.preventDefault();
  const taskName = event.target["task-name"].value;
  const taskDescription = event.target["task-description"].value;
  addTask(currentProjectId, taskName, taskDescription);
  event.target.reset();
  closeModal("task-form-modal");
}

document.getElementById("project-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const name = e.target["project-name"].value;
  const description = e.target["project-description"].value;
  addProject(name, description);
  closeModal("project-form-modal");
  e.target.reset();
});

document.getElementById("add-project-btn").onclick = () => {
  openModal("project-form-modal");
};

// Add a global event listener for dynamically created close buttons
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("close-btn")) {
    closeModal(e.target.closest(".modal").id);
  }
});

function openModal(modalId) {
  document.getElementById(modalId).style.display = "block";
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = "none";
}

document
  .getElementById("task-form")
  .addEventListener("submit", handleTaskFormSubmit);

document.addEventListener("DOMContentLoaded", () => {
  console.log("JavaScript Loaded");
});

document.addEventListener("DOMContentLoaded", () => {
  console.log("JavaScript Loaded");

  // Event listener for "Add Project" button click
  document.getElementById("add-project-btn").addEventListener("click", () => {
    openModal("project-form-modal");
  });

  // Event listener for dynamically created project list items
  document.querySelectorAll(".project-list-item").forEach((item) => {
    item.addEventListener("click", () => {
      const projectId = item.getAttribute("data-project-id");
      displayProject(projectId);
    });

    // Event listener for delete button within each project item
    const deleteButton = item.querySelector(".delete-btn");
    deleteButton.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent click event from bubbling to parent (project-list-item)
      const projectId = item.getAttribute("data-project-id");
      deleteProject(projectId);
    });
  });
});

// Function to handle project deletion
function deleteProject(projectId) {
  // Confirm deletion
  if (confirm("Are you sure you want to delete this project?")) {
    // Send AJAX request to delete project
    fetch(`/delete_project/${projectId}`, {
      method: "DELETE",
    })
      .then((response) => {
        if (response.ok) {
          // Remove project item from UI
          document
            .querySelector(`.project-list-item[data-project-id="${projectId}"]`)
            .remove();
          console.log(`Project ${projectId} deleted successfully.`);
        } else {
          console.error(`Failed to delete project ${projectId}.`);
        }
      })
      .catch((error) => {
        console.error("Error deleting project:", error);
      });
  }
}

// Function to open modal
function openModal(modalId) {
  document.getElementById(modalId).style.display = "block";
}

// Function to close modal
function closeModal(modalId) {
  document.getElementById(modalId).style.display = "none";
}

// Function to open modal
function openModal(modalId) {
  document.getElementById(modalId).style.display = "block";
}

// Function to close modal
function closeModal(modalId) {
  document.getElementById(modalId).style.display = "none";
}
