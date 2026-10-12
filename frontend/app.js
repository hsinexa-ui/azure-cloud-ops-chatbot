const API_BASE_URL = "http://127.0.0.1:8000";
const messages = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const connectionState = document.getElementById("connection-state");

function addMessage(text, role) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  const label = document.createElement("span");
  label.className = "label";
  label.textContent = role === "user" ? "YOU" : "BOT";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  message.append(label, paragraph);
  messages.appendChild(message);
  messages.scrollTop = messages.scrollHeight;
}

async function sendMessage(text) {
  addMessage(text, "user");
  input.value = "";
  connectionState.innerHTML = '<span class="dot"></span> Working';
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await response.json();
    addMessage(data.reply || "The API returned no message.", "bot");
    connectionState.innerHTML = `<span class="dot"></span> ${data.success ? "Ready" : "Needs attention"}`;
  } catch (error) {
    addMessage("I could not reach the backend. Start FastAPI and try again.", "bot");
    connectionState.innerHTML = '<span class="dot"></span> Offline';
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (text) sendMessage(text);
});

document.querySelectorAll("[data-message]").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.message));
});
