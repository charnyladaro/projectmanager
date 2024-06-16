// main.js

async function addProject(name, description) {
    const response = await fetch('/projects', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, description }),
    });

    if (response.ok) {
        const project = await response.json();
        projects.push({ id: project.id, name, description });
        displayProject(project.id);
    } else {
        console.error('Failed to add project');
    }
}

async function addTask(projectId, taskName, taskDescription) {
    const response = await fetch('/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: taskName, description: taskDescription, project_id: projectId }),
    });

    if (response.ok) {
        const task = await response.json();
        const taskElement = document.createElement('div');
        taskElement.classList.add('task');
        taskElement.id = `task-${task.id}`;
        taskElement.draggable = true;
        taskElement.ondragstart = drag;

        taskElement.innerHTML = `
            <span>${taskName} - <span id="time-logged-${task.id}">0</span> minutes</span>
            <div class="timer-controls">
                <button class="btn timer-btn" onclick="startTimer(${task.id})">Start Timer</button>
                <button class="btn timer-btn" onclick="pauseTimer(${task.id})">Pause Timer</button>
                <button class="btn timer-btn" onclick="stopTimer(${task.id})">Stop Timer</button>
            </div>
            <div class="timer-display" id="timer-display-${task.id}"></div>
        `;

        document.getElementById(`not-yet-started-${projectId}`).appendChild(taskElement);
    } else {
        console.error('Failed to add task');
    }
}

// Modify displayProject to fetch tasks from the backend
async function displayProject(projectId) {
    currentProjectId = projectId;

    const project = projects.find(proj => proj.id === projectId);
    const currentProjectContainer = document.getElementById('current-project');
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

    document.getElementById('add-task-btn').onclick = () => {
        openModal('task-form-modal');
    };

    // Fetch tasks for the current project
    const response = await fetch(`/projects/${projectId}/tasks`);
    if (response.ok) {
        const tasks = await response.json();
        tasks.forEach(task => {
            addTaskElement(projectId, task.id, task.name, task.description);
        });
    } else {
        console.error('Failed to fetch tasks');
    }
}

function addTaskElement(projectId, taskId, taskName, taskDescription) {
    const taskElement = document.createElement('div');
    taskElement.classList.add('task');
    taskElement.id = `task-${taskId}`;
    taskElement.draggable = true;
    taskElement.ondragstart = drag;

    taskElement.innerHTML = `
        <span>${taskName} - <span id="time-logged-${taskId}">0</span> minutes</span>
        <div class="timer-controls">
            <button class="btn timer-btn" onclick="startTimer(${taskId})">Start Timer</button>
            <button class="btn timer-btn" onclick="pauseTimer(${taskId})">Pause Timer</button>
            <button class="btn timer-btn" onclick="stopTimer(${taskId})">Stop Timer</button>
        </div>
        <div class="timer-display" id="timer-display-${taskId}"></div>
    `;

    document.getElementById(`not-yet-started-${projectId}`).appendChild(taskElement);
}

document.getElementById('project-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = e.target['project-name'].value;
    const description = e.target['project-description'].value;
    await addProject(name, description);
    closeModal('project-form-modal');
    e.target.reset();
});
