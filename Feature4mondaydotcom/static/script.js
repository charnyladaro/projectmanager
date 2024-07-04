let currentProjectId = null;
let timers = {};

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
      const fileListContainer = document.querySelector(".file-list ul");
      const uploadButton = document.getElementById("upload-button");

      projectTitle.textContent = `Project Details`;
      modalTasksContainer.innerHTML = "";
      fileListContainer.innerHTML = "";

      if (data.tasks.length > 0) {
        uploadButton.disabled = false;
      } else {
        uploadButton.disabled = true;
      }

      data.tasks.forEach((task) => {
        const taskDiv = document.createElement("div");
        taskDiv.classList.add("task");
        taskDiv.innerHTML = `
                <span>${task.name}</span>
                <span id="task-timer-${task.id}">${task.time_spent} seconds</span>
                <div class="task-buttons">
                    <button onclick="startTimer(${task.id})">Start</button>
                    <button onclick="stopTimer(${task.id})">Stop</button>
                    <button class="delete" onclick="deleteTask(${task.id})">Delete</button>
                </div>
            `;
        modalTasksContainer.appendChild(taskDiv);

        task.files.forEach((file) => {
          const fileListItem = document.createElement("li");
          fileListItem.innerHTML = `
                    <a href="/uploads/${file.file_path}" download>${file.file_path}</a>
                    <input type="button" value="Edit" class="Edit" onclick="editFileName(${file.id})"></input>
                    <a href="/uploads/${file.file_path}" download><button>Download</button></a>
                    <input type="button" value="Delete" class="delete" onclick="deleteFile(${file.id})"></input>
                `;
          fileListContainer.appendChild(fileListItem);
        });
      });

      document.getElementById("project-modal").style.display = "block";
    });
}
function addTaskToProject() {
  const taskName = document.getElementById("task-name").value;
  fetch(`/add_task_to_project`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name: taskName, project_id: currentProjectId }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showProjectDetails(currentProjectId);
      } else {
        alert(data.message);
      }
    });
}

function uploadFile() {
  const taskFile = document.getElementById("task-file").files[0];
  const formData = new FormData();

  formData.append("file", taskFile);
  formData.append("project_id", currentProjectId);

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
    let seconds = parseInt(
      document.getElementById(`task-timer-${taskId}`).innerText.split(" ")[0]
    );
    timers[taskId] = setInterval(() => {
      seconds++;
      document.getElementById(
        `task-timer-${taskId}`
      ).innerText = `${seconds} seconds`;
    }, 1000);
  }
}

function stopTimer(taskId) {
  if (timers[taskId]) {
    clearInterval(timers[taskId]);
    delete timers[taskId];
    updateTaskTimeSpent(taskId);
  }
}

function updateTaskTimeSpent(taskId) {
  const taskTimerElement = document.getElementById(`task-timer-${taskId}`);
  if (taskTimerElement) {
    const currentSeconds = parseInt(taskTimerElement.textContent.split(" ")[0]);
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
        closeModal();
      } else {
        alert(data.message); // Show the error message if deletion is not allowed
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
      } else {
        alert(data.message); // Show the error message if deletion is not allowed
      }
    });
}

function deleteFile(fileId) {
  fetch(`/delete_file`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ id: fileId }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showProjectDetails(currentProjectId); // Refresh the modal to update the file list
      } else {
        alert(data.message); // Show the error message if deletion is not allowed
      }
    });
}
function editFileName(fileId) {
  fetch(`/edit_file_name`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ id: fileId }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showProjectDetails(currentProjectId); // Refresh the modal to update the file list
      } else {
        alert(data.message); // Show the error message if deletion is not allowed
      }
    });
}
function closeModal() {
  document.getElementById("project-modal").style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
  loadProjects();
});
