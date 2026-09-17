const chatEl = document.getElementById("chat");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");

function addBubble(text, sender = "bot", isError = false) {
  const div = document.createElement("div");
  div.className = `msg ${sender}${isError ? " error" : ""}`;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
  return div;
}

function addWeatherCard(w) {
  const div = document.createElement("div");
  div.className = "card";
  div.innerHTML = `
    <h3>${w.location_name}${w.country ? ", " + w.country : ""}</h3>
    <div>${w.condition} ${w.is_day ? "☀️" : "🌙"}</div>
    <div class="grid">
      <div>Temp: <b>${w.temperature_c}°C / ${w.temperature_f}°F</b></div>
      <div>Feels like: <b>${w.feels_like_c}°C</b></div>
      <div>Humidity: <b>${w.humidity ?? "–"}%</b></div>
      <div>Wind: <b>${w.wind_speed_kmh ?? "–"} km/h</b></div>
    </div>
  `;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendMessage(message) {
  addBubble(message, "user");
  const typing = addBubble("SkyBot is thinking…", "bot");
  typing.classList.add("typing");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    typing.remove();

    if (!res.ok) {
      addBubble(data.detail || "Something went wrong.", "bot", true);
      return;
    }

    addBubble(data.reply, "bot", data.status === "error");
    if (data.status === "ok" && data.weather) {
      addWeatherCard(data.weather);
    }
  } catch (err) {
    typing.remove();
    addBubble("Network error — please try again.", "bot", true);
  }
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const value = inputEl.value.trim();
  if (!value) return;
  inputEl.value = "";
  sendMessage(value);
});

addBubble(
  "Hi! I'm SkyBot 🌤️ Ask me about the weather or temperature anywhere on Earth, e.g. \"What's the weather in Tokyo?\"",
  "bot"
);
