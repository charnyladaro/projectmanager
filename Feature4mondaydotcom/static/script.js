let currentProjectId = null;
let timers = {}; // Object to store timers for each task

function addProject() {
  const projectName = document.getElementById("project-name").value;

  fetch("/add_project", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name: projectName }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        loadProjects();
      }
    });

  document.getElementById("project-name").value = "";
}

function loadProjects() {
  fetch("/get_projects")
    .then((response) => response.json())
    .then((data) => {
      const projectsContainer = document.getElementById("projects");
      projectsContainer.innerHTML = "";

      data.projects.forEach((project) => {
        const projectDiv = document.createElement("div");
        projectDiv.classList.add("project");
        projectDiv.innerHTML = `
          <span onclick="showProjectDetails(${project.id})">${project.name}</span>
          <button class="delete" onclick="deleteProject(${project.id})">Delete</button>
        `;
        projectsContainer.appendChild(projectDiv);
      });
    });
}

function showProjectDetails(projectId) {
  currentProjectId = projectId;
  fetch(`/get_project_tasks?project_id=${projectId}`)
    .then((response) => response.json())
    .then((data) => {
      const modalTasksContainer = document.getElementById("modal-tasks");
      const projectTitle = document.getElementById("project-title");

      projectTitle.textContent = `Project Details (ID: ${projectId})`;
      modalTasksContainer.innerHTML = "";

      data.tasks.forEach((task) => {
        const taskDiv = document.createElement("div");
        taskDiv.classList.add("task");
        taskDiv.innerHTML = `
          <span>${task.name}</span>
          <span id="task-timer-${task.id}">${formatTime(task.time_spent)}</span>
          <div class="task-buttons">
            <button onclick="startTimer(${task.id})">Start</button>
            <button onclick="stopTimer(${task.id})">Stop</button>
            <button class="delete" onclick="deleteTask(${
              task.id
            })">Delete</button>
          </div>
        `;

        if (task.file_path) {
          const fileDisplay = document.createElement("div");

          if (isImageFile(task.file_path)) {
            const img = document.createElement("img");
            img.src = task.file_path;
            img.style.maxWidth = "100%";
            fileDisplay.appendChild(img);
          } else {
            const fileIcon = document.createElement("i");
            fileIcon.classList.add("fas", "fa-file");
            fileIcon.style.fontSize = "24px";
            fileDisplay.appendChild(fileIcon);
          }

          taskDiv.appendChild(fileDisplay);
        }

        modalTasksContainer.appendChild(taskDiv);
      });

      document.getElementById("project-modal").style.display = "block";
    });
}

function isImageFile(filePath) {
  return /\.(jpeg|jpg|png|gif)$/i.test(filePath);
}

function addTaskToProject() {
  const taskName = document.getElementById("task-name").value;
  const formData = new FormData();
  formData.append("name", taskName);
  formData.append("project_id", currentProjectId);

  fetch("/add_task_to_project", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showProjectDetails(currentProjectId);
      }
    });

  document.getElementById("task-name").value = "";
}

function uploadFileToProject() {
  const taskFile = document.getElementById("task-file").files[0];

  if (!taskFile) {
    alert("Please select a file to upload.");
    return;
  }

  const formData = new FormData();
  formData.append("project_id", currentProjectId);
  formData.append("file", taskFile);

  fetch("/upload_file_to_project", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showProjectDetails(currentProjectId);
      }
    });

  document.getElementById("task-file").value = "";
}

function startTimer(taskId) {
  if (!timers[taskId]) {
    let seconds = 0;
    const taskTimerElement = document.getElementById(`task-timer-${taskId}`);
    if (taskTimerElement) {
      const currentSeconds = parseInt(
        taskTimerElement.textContent
          .split(":")
          .reduce((acc, time) => 60 * acc + +time)
      );
      seconds = isNaN(currentSeconds) ? 0 : currentSeconds;
    }
    timers[taskId] = setInterval(() => {
      seconds++;
      updateTimerDisplay(taskId, seconds);
    }, 1000); // Update every second (1000 milliseconds)
  }
}

function stopTimer(taskId) {
  if (timers[taskId]) {
    clearInterval(timers[taskId]);
    timers[taskId] = null;
    // Update task time spent in the database (optional)
    updateTaskTimeSpent(taskId);
  }
}

function updateTaskTimeSpent(taskId) {
  const taskTimerElement = document.getElementById(`task-timer-${taskId}`);
  if (taskTimerElement) {
    const currentSeconds = taskTimerElement.textContent
      .split(":")
      .reduce((acc, time) => 60 * acc + +time);
    fetch(`/update_task_time`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id: taskId, time_spent: currentSeconds }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          console.log(`Updated time spent for task ${taskId}`);
        }
      });
  }
}

function deleteProject(projectId) {
  fetch(`/delete_project`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ id: projectId }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        loadProjects();
      }
    });
}

function deleteTask(taskId) {
  fetch(`/delete_task`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ id: taskId }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showProjectDetails(currentProjectId);
      }
    });
}

function closeModal() {
  document.getElementById("project-modal").style.display = "none";
}

function formatTime(seconds) {
  const hours = Math.floor(seconds / 3600)
    .toString()
    .padStart(2, "0");
  const minutes = Math.floor((seconds % 3600) / 60)
    .toString()
    .padStart(2, "0");
  const secs = (seconds % 60).toString().padStart(2, "0");
  return `${hours}:${minutes}:${secs}`;
}

function updateTimerDisplay(taskId, seconds) {
  const taskTimerElement = document.getElementById(`task-timer-${taskId}`);
  if (taskTimerElement) {
    taskTimerElement.textContent = formatTime(seconds);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadProjects();
});
