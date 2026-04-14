"""
sensor_simulator.py
-------------------
Simulates IoT sensor readings from a smart farm.
In production, this module would be replaced by real sensor integrations
(e.g., MQTT streams from Arduino/Raspberry Pi field nodes).
"""

import random
from datetime import datetime


# Realistic operational ranges per crop type
SENSOR_PROFILES = {
    "tomato": {
        "soil_moisture": (30, 80),
        "temperature": (18, 32),
        "humidity": (40, 80),
        "ph": (6.0, 7.0),
        "nitrogen": (30, 80),
    },
    "wheat": {
        "soil_moisture": (20, 70),
        "temperature": (12, 28),
        "humidity": (35, 75),
        "ph": (5.5, 7.5),
        "nitrogen": (20, 70),
    },
    "pepper": {
        "soil_moisture": (25, 75),
        "temperature": (20, 35),
        "humidity": (45, 85),
        "ph": (6.0, 7.5),
        "nitrogen": (25, 75),
    },
}


def generate_sensor_data(crop_type: str = "tomato", zone_id: str = None) -> dict:
    """
    Generate a single snapshot of sensor readings for a farm zone.

    Args:
        crop_type: Type of crop being grown (affects expected ranges)
        zone_id:   Optional override for sensor zone identifier

    Returns:
        dict with timestamped sensor readings
    """
    profile = SENSOR_PROFILES.get(crop_type, SENSOR_PROFILES["tomato"])

    # Occasionally inject out-of-range values to trigger AI recommendations
    # (simulates real-world drift and stress events ~30% of the time)
    def maybe_stress(low, high, stress_low=None, stress_high=None):
        if random.random() < 0.3:
            if stress_low and random.random() < 0.5:
                return round(random.uniform(stress_low, low), 1)
            if stress_high:
                return round(random.uniform(high, stress_high), 1)
        return round(random.uniform(low, high), 1)

    m_low, m_high = profile["soil_moisture"]
    t_low, t_high = profile["temperature"]
    h_low, h_high = profile["humidity"]
    p_low, p_high = profile["ph"]
    n_low, n_high = profile["nitrogen"]

    return {
        "sensor_id": zone_id or f"ZONE-{random.randint(1, 5):02d}",
        "crop_type": crop_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "soil_moisture": maybe_stress(m_low, m_high, stress_low=8, stress_high=95),
        "temperature": maybe_stress(t_low, t_high, stress_low=None, stress_high=44),
        "humidity": maybe_stress(h_low, h_high, stress_low=20, stress_high=98),
        "ph": round(maybe_stress(p_low, p_high, stress_low=4.2, stress_high=8.8), 2),
        "nitrogen": maybe_stress(n_low, n_high, stress_low=5, stress_high=None),
        "light_intensity": round(random.uniform(200, 1400), 0),  # lux
    }


def generate_multi_zone_data(crop_type: str = "tomato", num_zones: int = 4) -> list:
    """Generate sensor readings for multiple farm zones simultaneously."""
    zones = [f"ZONE-{i+1:02d}" for i in range(num_zones)]
    return [generate_sensor_data(crop_type=crop_type, zone_id=z) for z in zones]
