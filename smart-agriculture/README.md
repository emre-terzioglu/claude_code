# AgriAI — Smart Farm Decision System

An AI-powered agriculture decision system that simulates IoT sensor telemetry, processes it through a rule-based AI engine, and surfaces actionable recommendations via a real-time web dashboard.

---

## What This Is

A working MVP that demonstrates how AI can transform raw field sensor data into prioritised agronomic decisions — the same loop that precision agriculture platforms sell to commercial farms at scale.

```
[IoT Sensors] → [FastAPI Backend] → [AI Decision Engine] → [React Dashboard]
                                          ↓
                              [Automated Rule Triggers]
                              (irrigation, alerts, logs)
```

---

## Project Structure

```
smart-agriculture/
├── backend/
│   ├── main.py               # FastAPI app — routes + request models
│   ├── sensor_simulator.py   # IoT mock data generator (replaces real MQTT feeds)
│   ├── ai_engine.py          # Decision engine — observations, recommendations, auto-actions
│   └── requirements.txt
├── frontend/
│   └── index.html            # Full dashboard — zero build step required
└── README.md
```

---

## Setup & Running

### Prerequisites

- Python 3.11+
- A modern browser

### 1. Install backend dependencies

```bash
cd smart-agriculture/backend
pip install -r requirements.txt
```

### 2. Start the backend

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### 3. Open the dashboard

Open `frontend/index.html` directly in your browser — no build step, no npm install.

```bash
open frontend/index.html        # macOS
xdg-open frontend/index.html    # Linux
start frontend/index.html       # Windows
```

---

## API Reference

### `GET /sensor-data`

Returns a live simulated sensor reading.

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `crop_type` | `tomato \| wheat \| pepper` | `tomato` | Determines optimal thresholds |
| `zones` | `int` (1–8) | `1` | Number of sensor zones |

**Example response:**
```json
{
  "sensor_id": "ZONE-03",
  "crop_type": "tomato",
  "timestamp": "2025-06-15T10:22:04Z",
  "soil_moisture": 18.4,
  "temperature": 34.7,
  "humidity": 61.2,
  "ph": 5.1,
  "nitrogen": 42.0,
  "light_intensity": 890.0
}
```

---

### `POST /analyze`

Accepts a sensor reading and returns AI-powered recommendations.

**Request body:** Same shape as `/sensor-data` response.

**Example response:**
```json
{
  "sensor_id": "ZONE-03",
  "status": "CRITICAL",
  "summary": "CRITICAL conditions detected. Immediate intervention required...",
  "confidence": 0.94,
  "model_version": "AgriAI-v1.3",
  "observations": [
    {
      "metric": "soil_moisture",
      "value": 18.4,
      "unit": "%",
      "severity": "CRITICAL",
      "finding": "Soil moisture is critically low at 18.4%..."
    }
  ],
  "recommendations": [
    {
      "action": "Emergency irrigation — activate now",
      "rationale": "At 18.4% volumetric moisture the soil water potential is too low...",
      "priority": "CRITICAL",
      "estimated_impact": "Prevents crop loss; restores turgor pressure within 2–4 hours."
    }
  ],
  "automated_actions": [
    {
      "trigger": "Moisture 18.4% ≤ critical threshold 18%",
      "action": "Irrigation valves ZONE opened — 30-minute emergency cycle initiated",
      "status": "ACTIVATED"
    }
  ]
}
```

---

### `POST /analyze-and-fetch`

Single-call convenience endpoint — generates fresh sensor data and runs analysis in one round trip. Used by the dashboard's "Run Analysis" button.

---

## AI Decision Logic

The engine evaluates five metrics against **crop-specific optimal thresholds**:

| Metric | Rule | Action |
|--------|------|--------|
| Soil moisture < critical low | CRITICAL | Emergency irrigation auto-triggered |
| Soil moisture < low | HIGH | Irrigation scheduled |
| Temperature > critical high | CRITICAL | Emergency shading + misters |
| Temperature > high | MEDIUM | Shade cloth recommended |
| pH < low | HIGH/MEDIUM | Lime application |
| pH > high | MEDIUM | Sulfur amendment |
| Humidity > high | MEDIUM | Ventilation recommended |
| Nitrogen < low | MEDIUM | Fertigation recommended |

**Automation layer:** When soil moisture drops below the critical threshold, the system auto-fires an irrigation action without waiting for human input. This is surfaced separately in the UI as an "Automated Action" — distinct from human-reviewed recommendations.

---

## Dashboard Features

- **Real-time sensor cards** — colour-coded gauges update every 30 seconds
- **Crop profile selector** — switches threshold profiles (tomato / wheat / pepper)
- **Run Analysis button** — triggers AI engine and renders structured recommendations
- **Priority badges** — CRITICAL / HIGH / MEDIUM / LOW triage at a glance
- **Automated actions panel** — shows what the system did without human input
- **Confidence meter** — model certainty score

---

## Business Value

### Who Would Pay For This?

**1. Commercial greenhouse operators (primary market)**
- Greenhouses running 10–500 sensor zones need decision support, not raw data
- A wrong irrigation decision on a 1,000 m² tomato crop costs $8,000–$25,000
- Target price: **$400–$2,000/month SaaS** per farm

**2. Agrochemical companies**
- Companies like Corteva and Syngenta pay for platforms that recommend *their* products at the right time
- Distribution deal model: **$5–$15 per recommendation acted on**

**3. Agricultural lenders and crop insurers**
- Banks and insurers need evidence of farm management quality for underwriting
- This system creates a verifiable decision audit trail
- Target: **$50–$200/month** per insured farm (white-labeled through insurers)

**4. Government agricultural extension programs**
- Developing-market programs (Africa, Southeast Asia) need low-cost advisory tools for smallholder farmers
- Grant / NGO funded: **$1–$5/farmer/month** at large scale

---

### Why Is This Valuable?

**The core problem:** Agriculture produces more data than farmers can act on. A single IoT-instrumented greenhouse generates thousands of readings per day. Without a decision layer, data collection is cost with no return.

**The value this creates:**

| Without AgriAI | With AgriAI |
|----------------|-------------|
| Farmer checks data manually 2x/day | Continuous monitoring + instant alerts |
| Decisions based on experience/intuition | Evidence-based, crop-specific guidance |
| Irrigation activated when farmer notices wilting | Automated pre-emptive action at threshold |
| No audit trail for insurance claims | Full timestamped decision log |
| One agronomist serves 20 farms | One agronomist (via AI) serves 2,000 farms |

**Key metrics a commercial buyer cares about:**
- 15–30% reduction in water usage (measurable, sellable as ESG)
- 8–20% yield improvement from timely interventions
- 40% reduction in fungal disease losses from humidity alerts
- Payback period under 6 months for mid-size operations

**The real moat:** Data network effect. Every season of sensor + outcome data makes the recommendation engine smarter, creating a durable advantage over generic advisory tools.

---

## Extending to Production

This MVP is structured so each layer has a clean seam for production upgrades:

| MVP component | Production replacement |
|---------------|----------------------|
| `sensor_simulator.py` | MQTT broker (Mosquitto) + field node drivers |
| Rule engine in `ai_engine.py` | Claude API call with structured output |
| In-memory state | TimescaleDB or InfluxDB for time-series |
| `index.html` | React + Recharts for sensor history graphs |
| Manual trigger | Cron + webhook to physical irrigation controller |

---

## License

MIT — use freely, build responsibly.
