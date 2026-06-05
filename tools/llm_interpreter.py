import argparse
import json
import socket
import sys
import urllib.error
import urllib.request


DEFAULT_ENDPOINT = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "llama3.1:8b"


def ollama_tags_endpoint(endpoint):
    if endpoint.endswith("/api/generate"):
        return endpoint[: -len("/api/generate")] + "/api/tags"
    return endpoint.rstrip("/") + "/api/tags"


def ollama_status(endpoint=DEFAULT_ENDPOINT, model=DEFAULT_MODEL, timeout=2.0):
    tags_endpoint = ollama_tags_endpoint(endpoint)
    try:
        request = urllib.request.Request(tags_endpoint, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = [str(item.get("name") or item.get("model")) for item in data.get("models", [])]
        return {
            "available": response.status == 200,
            "endpoint": endpoint,
            "tags_endpoint": tags_endpoint,
            "model": model,
            "model_loaded": model in models,
            "models": models,
            "error": None,
        }
    except (urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
        return {"available": False, "endpoint": endpoint, "tags_endpoint": tags_endpoint, "model": model, "error": str(exc)}


def build_prompt(payload):
    compact_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        "Sen bir endustriyel motor izleme operator yardimcisisin.\n"
        "Kurallar:\n"
        "- Siniflandirma yapma ve model kararini degistirme.\n"
        "- Sadece verilen binary karar, multiclass olasiliklari, XAI feature etkileri ve sensor ozetini yorumla.\n"
        "- Cevap Turkce, kisa ve operator odakli olsun.\n"
        "- En fazla 4 madde yaz: durum, risk nedeni, dikkat edilecek sensorler, sonraki kontrol.\n"
        "- Emin degilsen bunu acikca belirt.\n\n"
        "Verilen model/XAI ciktisi:\n"
        f"{compact_payload}\n\n"
        "Operator yorumu:"
    )


def deterministic_fallback_summary(payload):
    prediction = payload.get("binary_prediction", {})
    alarm = prediction.get("alarm") or "n/a"
    instant_prediction = prediction.get("binary_prediction") or "n/a"
    anomaly_probability = prediction.get("anomaly_probability")
    probabilities = payload.get("multiclass_probabilities", {}) or {}
    top_class = "n/a"
    if probabilities:
        top_class = max(probabilities.items(), key=lambda item: float(item[1] or 0.0))[0]

    top_features = payload.get("xai_top_features", []) or []
    feature_names = [str(row.get("feature", "feature")) for row in top_features[:3]]
    sensor_summary = payload.get("sensor_summary", {}) or {}
    gyro = sensor_summary.get("gyro_mag_p95") or sensor_summary.get("gyro_mag_mean")
    pulse = sensor_summary.get("pulse_rate_hz_mean")

    if anomaly_probability is None:
        probability_text = "olasılık yok"
    else:
        probability_text = f"anomali olasiligi %{round(float(anomaly_probability) * 100)}"

    feature_text = ", ".join(feature_names) if feature_names else "belirgin XAI feature yok"
    gyro_text = "n/a" if gyro is None else f"{float(gyro):.2f}"
    pulse_text = "n/a" if pulse is None else f"{float(pulse):.2f} Hz"
    return (
        f"- Durum: anlik tahmin `{instant_prediction}`, smoothing alarmi `{alarm}`, {probability_text}; multiclass en yakin sinif `{top_class}`.\n"
        f"- Risk nedeni: XAI tarafinda one cikan feature'lar {feature_text}.\n"
        f"- Sensorler: gyro ozeti {gyro_text}, pulse ortalamasi {pulse_text}.\n"
        "- Sonraki kontrol: bu yorum local LLM degil deterministik fallback; Ollama modeli duzeltilince LLM yorumu tekrar denenmeli."
    )


def generate_operator_summary(
    payload,
    model=DEFAULT_MODEL,
    endpoint=DEFAULT_ENDPOINT,
    timeout=25.0,
):
    prompt = build_prompt(payload)
    request_payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.85,
            "num_predict": 220,
        },
    }
    try:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {
            "available": True,
            "model": model,
            "summary": str(data.get("response", "")).strip(),
            "role": "commentary_only_not_classifier",
            "error": None,
        }
    except (urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "model": model,
            "summary": deterministic_fallback_summary(payload),
            "role": "deterministic_fallback_not_classifier",
            "error": str(exc),
        }


def sample_payload():
    return {
        "binary_prediction": {"alarm": "anomaly", "anomaly_probability": 0.91},
        "multiclass_probabilities": {
            "normal": 0.03,
            "vibration": 0.63,
            "load": 0.08,
            "damping": 0.04,
            "stall_risk": 0.06,
            "mixed_anomaly": 0.16,
        },
        "xai_top_features": [
            {"feature": "motion__gyro_mag_p95", "focus_probability_delta": 0.28, "baseline_delta": 14.2},
            {"feature": "motion__gx_rms", "focus_probability_delta": 0.18, "baseline_delta": 7.4},
        ],
        "sensor_summary": {"gyro_mag_p95": 18.5, "acc_mag_mean": 1.04, "pulse_rate_hz_mean": 52.1},
        "validation_warnings": ["damping family holdout recall was weak in prior validation."],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a local Ollama operator summary from model/XAI output.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--payload-json", default=None, help="Optional JSON string payload.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.sample:
        payload = sample_payload()
    elif args.payload_json:
        payload = json.loads(args.payload_json)
    else:
        payload = json.loads(sys.stdin.read())
    result = generate_operator_summary(payload, model=args.model, endpoint=args.endpoint, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
