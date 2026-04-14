"""
main.py
-------
FastAPI application for the Smart Agriculture AI Decision System.

Architecture:
  /sensor-data  → Returns simulated real-time sensor readings
  /analyze      → Accepts sensor data and returns AI recommendations
  /auto-monitor → Background simulation of the automated alert loop
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional

from sensor_simulator import generate_sensor_data, generate_multi_zone_data
from ai_engine import analyze

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Smart Agriculture AI API",
    description="AI-powered decision system for precision agriculture",
    version="1.0.0",
)

# Allow all origins for demo purposes.
# In production: restrict to your frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SensorReading(BaseModel):
    """Incoming sensor data submitted for analysis."""
    sensor_id: str = Field(default="ZONE-01", description="Unique zone/sensor identifier")
    crop_type: Literal["tomato", "wheat", "pepper"] = Field(
        default="tomato", description="Crop type determines optimal threshold profiles"
    )
    timestamp: Optional[str] = Field(default=None)
    soil_moisture: float = Field(..., ge=0, le=100, description="Volumetric soil moisture %")
    temperature: float = Field(..., ge=-10, le=60, description="Ambient temperature °C")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity %")
    ph: float = Field(..., ge=0, le=14, description="Soil pH")
    nitrogen: Optional[float] = Field(default=50, ge=0, le=200, description="Available nitrogen mg/kg")
    light_intensity: Optional[float] = Field(default=800, description="Light intensity in lux")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    """Health check — confirms the API is running."""
    return {"status": "online", "service": "Smart Agriculture AI API", "version": "1.0.0"}


@app.get("/sensor-data", tags=["Sensors"])
def get_sensor_data(
    crop_type: Literal["tomato", "wheat", "pepper"] = Query(
        default="tomato", description="Crop profile to simulate"
    ),
    zones: int = Query(default=1, ge=1, le=8, description="Number of sensor zones to return"),
):
    """
    Returns simulated real-time sensor readings.

    In production this endpoint would proxy live MQTT/HTTP sensor streams.
    The simulator injects realistic stress events ~30% of the time to ensure
    the AI engine has interesting data to work with during demos.
    """
    if zones == 1:
        return generate_sensor_data(crop_type=crop_type)
    return generate_multi_zone_data(crop_type=crop_type, num_zones=zones)


@app.post("/analyze", tags=["AI Engine"])
def analyze_sensor_data(reading: SensorReading):
    """
    Accepts a sensor reading and returns AI-powered agronomic recommendations.

    The engine evaluates soil moisture, temperature, pH, humidity, and
    nitrogen against crop-specific optimal thresholds. It returns:
      - Structured observations (what is wrong and why it matters)
      - Prioritised recommendations (what to do)
      - Automated actions (what the system triggered without human input)
    """
    try:
        sensor_dict = reading.model_dump()
        result = analyze(sensor_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze-and-fetch", tags=["AI Engine"])
def analyze_fresh_data(
    crop_type: Literal["tomato", "wheat", "pepper"] = Query(default="tomato"),
):
    """
    Convenience endpoint: fetches a fresh sensor reading and immediately
    runs AI analysis. Useful for the dashboard's single-click "Run Analysis" flow.
    """
    sensor_data = generate_sensor_data(crop_type=crop_type)
    result = analyze(sensor_data)
    return {"sensor_data": sensor_data, "analysis": result}
