document.addEventListener("DOMContentLoaded", function () {
  const taskList = document.getElementById("task-list");
  const timers = {};
  const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");

  taskList.addEventListener("click", function (e) {
    const taskId = e.target.dataset.taskId;

    if (e.target.classList.contains("start-timer")) {
      startTimer(taskId);
    } else if (e.target.classList.contains("stop-timer")) {
      stopTimer(taskId);
    } else if (e.target.classList.contains("delete-file")) {
      deleteFile(taskId);
    } else if (e.target.classList.contains("delete-task")) {
      deleteTask(taskId);
    }
  });

  function startTimer(taskId) {
    const timerElement = document.querySelector(
      `.timer[data-task-id="${taskId}"]`
    );
    const startButton = document.querySelector(
      `.start-timer[data-task-id="${taskId}"]`
    );
    const stopButton = document.querySelector(
      `.stop-timer[data-task-id="${taskId}"]`
    );

    let seconds = 0;
    timers[taskId] = setInterval(() => {
      seconds++;
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const secs = seconds % 60;
      timerElement.textContent = `${String(hours).padStart(2, "0")}:${String(
        minutes
      ).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    }, 1000);

    startButton.style.display = "none";
    stopButton.style.display = "inline-block";
  }

  function stopTimer(taskId) {
    const timerElement = document.querySelector(
      `.timer[data-task-id="${taskId}"]`
    );
    const startButton = document.querySelector(
      `.start-timer[data-task-id="${taskId}"]`
    );
    const stopButton = document.querySelector(
      `.stop-timer[data-task-id="${taskId}"]`
    );

    clearInterval(timers[taskId]);
    delete timers[taskId];

    const time = timerElement.textContent.split(":");
    const hours = parseInt(time[0]);
    const minutes = parseInt(time[1]);
    const seconds = parseInt(time[2]);
    const totalHours = hours + minutes / 60 + seconds / 3600;

    fetch("/track_time", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: `task_id=${taskId}&time_spent=${totalHours}`,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          alert("Time tracked successfully!");
        } else {
          alert("Error tracking time.");
        }
      });

    startButton.style.display = "inline-block";
    stopButton.style.display = "none";
  }

  function deleteFile(fileId) {
    if (confirm("Are you sure you want to delete this file?")) {
      fetch(`/delete_file/${fileId}`, {
        method: "DELETE",
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            const fileElement = document.querySelector(
              `.uploaded-file button[data-file-id="${fileId}"]`
            ).parentNode;
            fileElement.remove();
          } else {
            alert("Error deleting file.");
          }
        });
    }
  }

  document.addEventListener("click", function (e) {
    if (e.target.classList.contains("delete-file")) {
      const fileId = e.target.dataset.fileId;
      deleteFile(fileId);
    }
  });

  function deleteTask(taskId) {
    if (confirm("Are you sure you want to delete this task?")) {
      fetch(`/delete_task/${taskId}`, {
        method: "DELETE",
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            alert("Task deleted successfully!");
            location.reload();
          } else {
            alert("Error deleting task.");
          }
        });
    }
  }
});

fetch("/get-csrf-token")
  .then((response) => response.json())
  .then((data) => {
    const csrfToken = data.csrf_token;
    // Use this token in your fetch headers
  });

document.addEventListener("DOMContentLoaded", function () {
  const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");

  document.querySelectorAll(".delete-project").forEach((button) => {
    button.addEventListener("click", function () {
      const projectId = this.getAttribute("data-project-id");
      if (confirm("Are you sure you want to delete this project?")) {
        fetch(`/delete_project/${projectId}`, {
          method: "DELETE",
          headers: {
            "X-CSRFToken": csrfToken,
          },
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              // Remove the project from the DOM
              this.closest(".project-item").remove();
            } else {
              alert("Failed to delete project");
            }
          })
          .catch((error) => {
            console.error("Error:", error);
            alert("An error occurred while deleting the project");
          });
      }
    });
  });
});

document.addEventListener("DOMContentLoaded", function () {
  const deleteFileButtons = document.querySelectorAll(".delete-file-btn");
  deleteFileButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const fileId = this.dataset.fileId;
      if (confirm("Are you sure you want to delete this file?")) {
        const csrfToken = document
          .querySelector('meta[name="csrf-token"]')
          .getAttribute("content");

        fetch(`/delete_file/${fileId}`, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({}),
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              this.closest(".uploaded-file").remove();
              alert("File deleted successfully");
            } else {
              alert(`Failed to delete file: ${data.message}`);
            }
          })
          .catch((error) => {
            console.error("Error:", error);
            alert("An error occurred while deleting the file.");
          });
      }
    });
  });
});

document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("assignUsersModal");
  const openModalBtn = document.getElementById("openAssignUsersModal");
  const closeModalBtn = document.getElementById("closeModal");
  const saveAssignedUsersBtn = document.getElementById("saveAssignedUsers");
  const addTaskForm = document.getElementById("addTaskForm");

  openModalBtn.onclick = function () {
    modal.style.display = "block";
  };

  closeModalBtn.onclick = function () {
    modal.style.display = "none";
  };

  saveAssignedUsersBtn.onclick = function () {
    const selectedUsers = document.querySelectorAll(
      'input[name="assigned_to"]:checked'
    );
    const assignedUserIds = Array.from(selectedUsers).map(
      (checkbox) => checkbox.value
    );

    // Remove any existing hidden inputs for assigned users
    const existingInputs = addTaskForm.querySelectorAll(
      'input[name="assigned_to[]"]'
    );
    existingInputs.forEach((input) => input.remove());

    // Add new hidden inputs for each selected user
    assignedUserIds.forEach((userId) => {
      const hiddenInput = document.createElement("input");
      hiddenInput.type = "hidden";
      hiddenInput.name = "assigned_to[]";
      hiddenInput.value = userId;
      addTaskForm.appendChild(hiddenInput);
    });

    modal.style.display = "none";
  };

  window.onclick = function (event) {
    if (event.target == modal) {
      modal.style.display = "none";
    }
  };
});

document.getElementById("profile_picture").onchange = function (evt) {
  var tgt = evt.target || window.event.srcElement,
    files = tgt.files;

  // FileReader support
  if (FileReader && files && files.length) {
    var fr = new FileReader();
    fr.onload = function () {
      document.getElementById("profile-preview").src = fr.result;
    };
    fr.readAsDataURL(files[0]);
  }
};


var csrftoken = document.querySelector('meta[name=csrf-token]').getAttribute('content')

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    }
})

