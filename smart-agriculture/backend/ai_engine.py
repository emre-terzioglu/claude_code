"""
ai_engine.py
------------
Rule-based AI decision engine for smart agriculture.

Design intent: Mimics the structured output of an LLM-based agent while
remaining deterministic and testable. In a production system, this module's
`build_prompt()` output would be sent to a Claude/GPT endpoint; the rule
layer here acts as a fast, offline fallback and cost saver.
"""

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Optimal thresholds per crop type
# ---------------------------------------------------------------------------
CROP_THRESHOLDS = {
    "tomato": {
        "soil_moisture": {"low": 30, "critical_low": 18, "high": 80},
        "temperature":   {"high": 33, "critical_high": 38},
        "humidity":      {"high": 82},
        "ph":            {"low": 5.8, "high": 7.2},
        "nitrogen":      {"low": 25},
    },
    "wheat": {
        "soil_moisture": {"low": 22, "critical_low": 12, "high": 72},
        "temperature":   {"high": 30, "critical_high": 36},
        "humidity":      {"high": 78},
        "ph":            {"low": 5.5, "high": 7.5},
        "nitrogen":      {"low": 18},
    },
    "pepper": {
        "soil_moisture": {"low": 25, "critical_low": 15, "high": 78},
        "temperature":   {"high": 36, "critical_high": 40},
        "humidity":      {"high": 88},
        "ph":            {"low": 6.0, "high": 7.5},
        "nitrogen":      {"low": 22},
    },
}

# Default to tomato thresholds for unknown crop types
DEFAULT_CROP = "tomato"


@dataclass
class Observation:
    """A single sensor anomaly detected by the engine."""
    metric: str
    value: float
    unit: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    finding: str


@dataclass
class Recommendation:
    """An actionable recommendation generated from an observation."""
    action: str
    rationale: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    estimated_impact: str


@dataclass
class AutomatedAction:
    """An action the system triggered automatically (no human needed)."""
    trigger: str
    action: str
    status: Literal["ACTIVATED", "SCHEDULED", "MONITORING"]


@dataclass
class AnalysisResult:
    """Full structured response from the AI engine."""
    sensor_id: str
    crop_type: str
    timestamp: str
    status: Literal["OPTIMAL", "ATTENTION_NEEDED", "CRITICAL"]
    summary: str
    observations: list[Observation] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    automated_actions: list[AutomatedAction] = field(default_factory=list)
    confidence: float = 0.95
    model_version: str = "AgriAI-v1.3"


# ---------------------------------------------------------------------------
# Core analysis logic
# ---------------------------------------------------------------------------

def analyze(sensor_data: dict) -> dict:
    """
    Analyze a sensor reading dict and return a structured AI-style response.

    This is the main entry point called by the API layer.
    """
    crop = sensor_data.get("crop_type", DEFAULT_CROP)
    thresholds = CROP_THRESHOLDS.get(crop, CROP_THRESHOLDS[DEFAULT_CROP])

    observations: list[Observation] = []
    recommendations: list[Recommendation] = []
    automated_actions: list[AutomatedAction] = []

    # --- Soil Moisture ---
    moisture = sensor_data.get("soil_moisture", 50)
    moisture_t = thresholds["soil_moisture"]

    if moisture <= moisture_t["critical_low"]:
        obs = Observation(
            metric="soil_moisture", value=moisture, unit="%",
            severity="CRITICAL",
            finding=f"Soil moisture is critically low at {moisture}% — well below the {moisture_t['critical_low']}% danger threshold. Crop stress and wilting are imminent."
        )
        observations.append(obs)
        recommendations.append(Recommendation(
            action="Emergency irrigation — activate now",
            rationale=f"At {moisture}% volumetric moisture the soil water potential is too low for root uptake. Immediate irrigation prevents irreversible yield loss.",
            priority="CRITICAL",
            estimated_impact="Prevents crop loss; restores turgor pressure within 2–4 hours."
        ))
        # AUTO-TRIGGER: Below critical threshold → system acts without human input
        automated_actions.append(AutomatedAction(
            trigger=f"Moisture {moisture}% ≤ critical threshold {moisture_t['critical_low']}%",
            action="Irrigation valves ZONE opened — 30-minute emergency cycle initiated",
            status="ACTIVATED"
        ))

    elif moisture < moisture_t["low"]:
        obs = Observation(
            metric="soil_moisture", value=moisture, unit="%",
            severity="HIGH",
            finding=f"Soil moisture ({moisture}%) is below the optimal lower bound of {moisture_t['low']}%. Crop growth rate will slow without intervention."
        )
        observations.append(obs)
        recommendations.append(Recommendation(
            action="Schedule irrigation within 2 hours",
            rationale=f"Moisture is {moisture_t['low'] - moisture:.0f} percentage points below target range. A 20-minute drip cycle should restore adequate levels.",
            priority="HIGH",
            estimated_impact="Maintains growth rate and prevents stress response."
        ))
        # AUTO-TRIGGER: Below low threshold → schedule irrigation
        automated_actions.append(AutomatedAction(
            trigger=f"Moisture {moisture}% < optimal threshold {moisture_t['low']}%",
            action="Irrigation schedule queued — next cycle in 90 minutes",
            status="SCHEDULED"
        ))

    # --- Temperature ---
    temp = sensor_data.get("temperature", 22)
    temp_t = thresholds["temperature"]

    if temp >= temp_t["critical_high"]:
        observations.append(Observation(
            metric="temperature", value=temp, unit="°C",
            severity="CRITICAL",
            finding=f"Temperature has reached {temp}°C — exceeding the {temp_t['critical_high']}°C critical threshold. Enzymatic processes and pollination are disrupted."
        ))
        recommendations.append(Recommendation(
            action="Deploy emergency shading + activate cooling misters",
            rationale=f"At {temp}°C, protein denaturation in plant cells begins. Immediate shading (60–70% exclusion cloth) combined with evaporative cooling can reduce canopy temperature by 5–8°C.",
            priority="CRITICAL",
            estimated_impact="Prevents heat-set failure and protects fruit quality."
        ))
    elif temp > temp_t["high"]:
        observations.append(Observation(
            metric="temperature", value=temp, unit="°C",
            severity="MEDIUM",
            finding=f"Temperature ({temp}°C) is above the recommended upper bound of {temp_t['high']}°C. Sustained exposure will reduce fruit set."
        ))
        recommendations.append(Recommendation(
            action="Install shade cloth (30–40% exclusion)",
            rationale="Moderate heat stress reduces photosynthetic efficiency. Shade cloth reduces radiative heat load without significantly impacting light-use efficiency.",
            priority="MEDIUM",
            estimated_impact="Reduces canopy temperature by 3–5°C; improves fruit set by ~15%."
        ))

    # --- Soil pH ---
    ph = sensor_data.get("ph", 6.5)
    ph_t = thresholds["ph"]

    if ph < ph_t["low"]:
        severity = "HIGH" if ph < (ph_t["low"] - 0.5) else "MEDIUM"
        observations.append(Observation(
            metric="ph", value=ph, unit="pH",
            severity=severity,
            finding=f"Soil pH is acidic at {ph} — below the optimal range of {ph_t['low']}–{ph_t['high']}. Nutrient lockout (phosphorus, calcium, magnesium) is likely."
        ))
        dose = round((ph_t["low"] - ph) * 2.5, 1)  # rough lime dose estimate
        recommendations.append(Recommendation(
            action=f"Apply agricultural lime at ~{dose} kg/100m²",
            rationale=f"Acidic soil reduces availability of macronutrients. Liming raises pH and improves cation exchange capacity. Retest in 2–3 weeks.",
            priority=severity,
            estimated_impact="Unlocks bound nutrients; expected yield improvement of 8–20% over the season."
        ))

    elif ph > ph_t["high"]:
        severity = "HIGH" if ph > (ph_t["high"] + 0.5) else "MEDIUM"
        observations.append(Observation(
            metric="ph", value=ph, unit="pH",
            severity=severity,
            finding=f"Soil pH is alkaline at {ph} — above optimal range of {ph_t['low']}–{ph_t['high']}. Iron and manganese deficiency likely."
        ))
        recommendations.append(Recommendation(
            action="Apply elemental sulfur at 1–2 kg/100m²",
            rationale="Alkaline soil causes micronutrient lockout (Fe, Mn, Zn). Elemental sulfur is microbially oxidized to sulfuric acid, gradually lowering pH over 4–6 weeks.",
            priority=severity,
            estimated_impact="Restores micronutrient uptake; reduces chlorosis risk."
        ))

    # --- Humidity ---
    humidity = sensor_data.get("humidity", 60)
    hum_t = thresholds["humidity"]

    if humidity > hum_t["high"]:
        observations.append(Observation(
            metric="humidity", value=humidity, unit="%",
            severity="MEDIUM",
            finding=f"Relative humidity ({humidity}%) exceeds {hum_t['high']}%. High humidity creates conditions favourable for fungal pathogens (Botrytis, powdery mildew)."
        ))
        recommendations.append(Recommendation(
            action="Activate ventilation fans and increase air circulation",
            rationale="Reducing leaf wetness time is the primary lever for disease prevention. Target RH below 80% during fruiting stages.",
            priority="MEDIUM",
            estimated_impact="Reduces disease incidence by up to 40%; protects crop quality."
        ))

    # --- Nitrogen ---
    nitrogen = sensor_data.get("nitrogen", 50)
    nit_t = thresholds["nitrogen"]

    if nitrogen < nit_t["low"]:
        observations.append(Observation(
            metric="nitrogen", value=nitrogen, unit="mg/kg",
            severity="MEDIUM",
            finding=f"Available nitrogen ({nitrogen} mg/kg) is below the minimum threshold of {nit_t['low']} mg/kg. Stunted growth and yellowing (chlorosis) expected."
        ))
        recommendations.append(Recommendation(
            action="Apply balanced NPK fertilizer (fertigation recommended)",
            rationale="Nitrogen is the primary driver of vegetative growth. Fertigation ensures rapid uptake versus broadcast application.",
            priority="MEDIUM",
            estimated_impact="Restores growth rate within 5–7 days."
        ))

    # --- Build final result ---
    result = _build_result(sensor_data, observations, recommendations, automated_actions)
    return _serialize(result)


def _build_result(
    sensor_data: dict,
    observations: list[Observation],
    recommendations: list[Recommendation],
    automated_actions: list[AutomatedAction],
) -> AnalysisResult:
    """Determine overall status and compose the final result object."""
    severities = [o.severity for o in observations]

    if "CRITICAL" in severities:
        status = "CRITICAL"
        summary = (
            f"CRITICAL conditions detected in {sensor_data.get('sensor_id', 'unknown zone')}. "
            f"Immediate intervention required to prevent crop loss. "
            f"{len(automated_actions)} automated action(s) have been triggered."
        )
    elif observations:
        status = "ATTENTION_NEEDED"
        summary = (
            f"{len(observations)} issue(s) detected requiring attention within the next few hours. "
            f"Crops are currently stressed but recoverable. "
            f"Follow recommendations in priority order."
        )
    else:
        status = "OPTIMAL"
        summary = (
            "All sensor readings are within optimal ranges for the current crop profile. "
            "No action required. Continue standard monitoring schedule."
        )

    return AnalysisResult(
        sensor_id=sensor_data.get("sensor_id", "UNKNOWN"),
        crop_type=sensor_data.get("crop_type", DEFAULT_CROP),
        timestamp=sensor_data.get("timestamp", ""),
        status=status,
        summary=summary,
        observations=observations,
        recommendations=recommendations,
        automated_actions=automated_actions,
        confidence=0.94,
        model_version="AgriAI-v1.3",
    )


def _serialize(result: AnalysisResult) -> dict:
    """Convert dataclass tree to a plain dict for JSON serialisation."""
    return {
        "sensor_id": result.sensor_id,
        "crop_type": result.crop_type,
        "timestamp": result.timestamp,
        "status": result.status,
        "summary": result.summary,
        "confidence": result.confidence,
        "model_version": result.model_version,
        "observations": [
            {
                "metric": o.metric,
                "value": o.value,
                "unit": o.unit,
                "severity": o.severity,
                "finding": o.finding,
            }
            for o in result.observations
        ],
        "recommendations": [
            {
                "action": r.action,
                "rationale": r.rationale,
                "priority": r.priority,
                "estimated_impact": r.estimated_impact,
            }
            for r in result.recommendations
        ],
        "automated_actions": [
            {
                "trigger": a.trigger,
                "action": a.action,
                "status": a.status,
            }
            for a in result.automated_actions
        ],
    }
