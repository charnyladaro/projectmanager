let timers = {};
let projects = [];
let currentProjectId = null;

async function fetchProjects() {
  const response = await fetch("/get_projects");
  if (response.ok) {
    const data = await response.json();
    projects = data.projects;
    console.log("Projects fetched:", projects);
    const projectList = document.getElementById("project-list");
    projectList.innerHTML = ""; // Clear the project list before appending new ones
    projects.forEach((project) => {
      const projectListItem = createProjectListItem(project);
      projectList.appendChild(projectListItem);
      if (currentProjectId === null) {
        displayProject(project.id);
        currentProjectId = project.id; // Set the current project ID to the first project
      }
    });
  } else {
    console.error("Failed to fetch projects:", response.statusText);
  }
}

async function addProject(name, description) {
  const response = await fetch("/add_project", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, description }),
  });

  if (response.ok) {
    const project = await response.json();
    projects.push(project);

    const projectListItem = createProjectListItem(project);
    document.getElementById("project-list").appendChild(projectListItem);

    if (currentProjectId === null) {
      displayProject(project.id);
    }
  } else {
    console.error("Failed to add project:", response.statusText);
  }
}

async function addTask(projectId, taskName, taskDescription) {
  const response = await fetch("/add_task", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: taskName,
      description: taskDescription,
      project_id: projectId,
    }),
  });

  if (response.ok) {
    const task = await response.json();
    const taskElement = document.createElement("div");
    taskElement.classList.add("task");
    taskElement.id = `task-${task.id}`;
    taskElement.draggable = true;
    taskElement.ondragstart = drag;

    taskElement.innerHTML = `
      <span>${task.name} - <span id="time-logged-${task.id}">0</span> minutes</span>
      <div class="timer-controls">
        <button class="btn timer-btn" onclick="startTimer(${task.id})">Start</button>
        <button class="btn timer-btn" onclick="pauseTimer(${task.id})">Pause</button>
        <button class="btn timer-btn" onclick="stopTimer(${task.id})">Stop</button>
      </div>
      <div class="timer-display" id="timer-display-${task.id}"></div>
    `;
    document
      .getElementById(`not-yet-started-${projectId}`)
      .appendChild(taskElement);
  } else {
    console.error("Failed to add task:", response.statusText);
  }
}

function displayProject(projectId) {
  currentProjectId = projectId;
  const project = projects.find((proj) => proj.id === projectId);
  console.log("Displaying project:", project);
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
      <div class="column" id="completed-${projectId}" ondrop="drop(event)" ondragover="allowDrop(event)">
        <h3>Completed Tasks</h3>
      </div>
    </div>
  `;
  document
    .getElementById("add-task-btn")
    .addEventListener("click", () =>
      openTaskFormModal(project.id, "Add Task", addTask)
    );
  project.tasks.forEach((task) => {
    const taskElement = document.createElement("div");
    taskElement.classList.add("task");
    taskElement.id = `task-${task.id}`;
    taskElement.draggable = true;
    taskElement.ondragstart = drag;

    taskElement.innerHTML = `
      <span>${task.name} - <span id="time-logged-${task.id}">0</span> minutes</span>
      <div class="timer-controls">
        <button class="btn timer-btn" onclick="startTimer(${task.id})">Start</button>
        <button class="btn timer-btn" onclick="pauseTimer(${task.id})">Pause</button>
        <button class="btn timer-btn" onclick="stopTimer(${task.id})">Stop</button>
      </div>
      <div class="timer-display" id="timer-display-${task.id}"></div>
    `;
    document
      .getElementById(`${task.status.toLowerCase()}-${projectId}`)
      .appendChild(taskElement);
  });
}

function createProjectListItem(project) {
  const projectListItem = document.createElement("div");
  projectListItem.classList.add("project-list-item");
  projectListItem.id = `project-list-item-${project.id}`;
  projectListItem.onclick = () => displayProject(project.id);

  const projectTitle = document.createElement("h3");
  projectTitle.textContent = project.name;

  const deleteButton = document.createElement("button");
  deleteButton.classList.add("btn", "delete-btn");
  deleteButton.textContent = "Delete";
  deleteButton.onclick = (event) => {
    event.stopPropagation();
    deleteProject(project.id);
  };

  projectListItem.appendChild(projectTitle);
  projectListItem.appendChild(deleteButton);

  return projectListItem;
}

async function deleteProject(projectId) {
  const response = await fetch("/delete_project", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_id: projectId }),
  });

  if (response.ok) {
    const result = await response.json();
    if (result.success) {
      projects = projects.filter((project) => project.id !== projectId);
      const projectListItem = document.getElementById(
        `project-list-item-${projectId}`
      );
      if (projectListItem) {
        projectListItem.remove();
      }
      if (currentProjectId === projectId) {
        currentProjectId = projects.length > 0 ? projects[0].id : null;
        if (currentProjectId !== null) {
          displayProject(currentProjectId);
        } else {
          document.getElementById("current-project").innerHTML = "";
        }
      }
    } else {
      console.error("Failed to delete project:", result.error);
    }
  } else {
    console.error("Failed to delete project:", response.statusText);
  }
}

// Timer functions
function startTimer(taskId) {
  if (!timers[taskId]) {
    timers[taskId] = {
      startTime: Date.now(),
      elapsedTime: 0,
      intervalId: setInterval(() => {
        const elapsedTime = Date.now() - timers[taskId].startTime;
        document.getElementById(`timer-display-${taskId}`).textContent =
          formatTime(timers[taskId].elapsedTime + elapsedTime);
      }, 1000),
    };
  } else {
    timers[taskId].startTime = Date.now();
    timers[taskId].intervalId = setInterval(() => {
      const elapsedTime = Date.now() - timers[taskId].startTime;
      document.getElementById(`timer-display-${taskId}`).textContent =
        formatTime(timers[taskId].elapsedTime + elapsedTime);
    }, 1000);
  }
}

function pauseTimer(taskId) {
  if (timers[taskId]) {
    clearInterval(timers[taskId].intervalId);
    timers[taskId].elapsedTime += Date.now() - timers[taskId].startTime;
  }
}

function stopTimer(taskId) {
  if (timers[taskId]) {
    clearInterval(timers[taskId].intervalId);
    const totalElapsedTime =
      timers[taskId].elapsedTime + (Date.now() - timers[taskId].startTime);
    const timeLoggedElement = document.getElementById(`time-logged-${taskId}`);
    const previousTimeLogged = parseInt(timeLoggedElement.textContent, 10);
    timeLoggedElement.textContent =
      previousTimeLogged + Math.floor(totalElapsedTime / 60000); // convert ms to minutes
    delete timers[taskId];
  }
}

function formatTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${hours}:${minutes}:${seconds}`;
}

function allowDrop(event) {
  event.preventDefault();
}

function drag(event) {
  event.dataTransfer.setData("text", event.target.id);
}

function drop(event) {
  event.preventDefault();
  const data = event.dataTransfer.getData("text");
  const taskElement = document.getElementById(data);
  event.target.appendChild(taskElement);
}

document.addEventListener("DOMContentLoaded", () => {
  fetchProjects();

  document
    .getElementById("add-project-btn")
    .addEventListener("click", () =>
      openProjectFormModal("Add Project", addProject)
    );

  // Close modals when clicking the close button
  document.querySelectorAll(".close-btn").forEach((closeBtn) => {
    closeBtn.addEventListener("click", () => {
      closeBtn.parentElement.parentElement.style.display = "none";
    });
  });

  // Close modals when clicking outside the modal content
  window.addEventListener("click", (event) => {
    if (event.target.classList.contains("modal")) {
      event.target.style.display = "none";
    }
  });
});

function openProjectFormModal(title, submitCallback) {
  const modal = document.getElementById("project-form-modal");
  modal.style.display = "block";
  const projectForm = document.getElementById("project-form");
  projectForm.onsubmit = (event) => {
    event.preventDefault();
    const formData = new FormData(projectForm);
    const name = formData.get("project-name");
    const description = formData.get("project-description");
    submitCallback(name, description);
    modal.style.display = "none";
    projectForm.reset();
  };
}

function openTaskFormModal(projectId, title, submitCallback) {
  const modal = document.getElementById("task-form-modal");
  modal.style.display = "block";
  const taskForm = document.getElementById("task-form");
  taskForm.onsubmit = (event) => {
    event.preventDefault();
    const formData = new FormData(taskForm);
    const name = formData.get("task-name");
    const description = formData.get("task-description");
    submitCallback(projectId, name, description);
    modal.style.display = "none";
    taskForm.reset();
  };
}
