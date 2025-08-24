const USER = "frontend_user";

let sensor = "temperature";
if (window.location.pathname.includes("gas")) sensor = "gas";
else if (window.location.pathname.includes("presence")) sensor = "presence";

const chartConfig = {
  temperature: { canvasId: "chartTemp", label: "Temperatura (°C)", color: "blue" },
  gas: { canvasId: "chartGas", label: "Gás (ppm)", color: "red" },
  presence: { canvasId: "chartPresence", label: "Presença", color: "green" }
};

const { canvasId, label, color } = chartConfig[sensor];

const ctx = document.getElementById(canvasId).getContext("2d");
const chart = new Chart(ctx, {
  type: "line",
  data: { labels: [], datasets: [{ label, data: [], borderColor: color, fill: false }] },
  options: {
    responsive: true,
    scales: { 
      x: { display: true }, 
      y: { beginAtZero: true, suggestedMax: sensor === "presence" ? 1.5 : undefined }
    }
  }
});

function pushPoint(value) {
  const now = new Date().toLocaleTimeString();
  chart.data.labels.push(now);
  chart.data.datasets[0].data.push(value);
  if (chart.data.labels.length > 30) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update();
}
fetch(`http://localhost:8000/token?user=${USER}`)
  .then(res => res.json())
  .then(data => {
    const token = data.token;
    console.log("Token JWT recebido:", token);

    const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
    ws.onopen = () => console.log("WebSocket conectado");
    ws.onclose = () => console.log("WebSocket desconectado");
    ws.onerror = (e) => console.error("WebSocket erro", e);

    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);

      if (msg.type === "ALERTA_SEGURANCA") {
        console.warn("ALERTA DE SEGURANÇA RECEBIDO:", msg);
        const alertsList = document.getElementById("alerts-list");
        const alertElement = document.createElement("div");
        alertElement.className = "alert-item";
        
        const timestamp = new Date().toLocaleString();
        
        alertElement.innerHTML = `<strong>[${timestamp}]</strong> Ataque Detectado: <em>${msg.attack}</em> no tópico "${msg.topic}".`;
        
        alertsList.prepend(alertElement);

      } else {
        const payload = msg.payload;
        if (payload && payload.sensor === sensor) {
          pushPoint(payload.value);
        }
      }
    };
  })
  .catch(err => console.error("Erro ao obter token JWT:", err));
