const API = "http://localhost:3000/tasks";

async function loadTasks(){
  const res = await fetch(API);
  const tasks = await res.json();

  const list = document.getElementById("taskList");
  list.innerHTML = "";

  tasks.forEach(task => {
    list.innerHTML += `
      <li>
        ${task.title}
        <button onclick="deleteTask(${task.id})">X</button>
      </li>
    `;
  });
}

async function addTask(){
  const input = document.getElementById("taskInput");

  if(input.value.trim() === "") return;

  await fetch(API,{
    method:"POST",
    headers:{
      "Content-Type":"application/json"
    },
    body: JSON.stringify({
      title: input.value
    })
  });

  input.value="";
  loadTasks();
}

async function deleteTask(id){
  await fetch(API + "/" + id,{
    method:"DELETE"
  });

  loadTasks();
}

loadTasks();