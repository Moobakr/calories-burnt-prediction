"""Small WSGI inference app: frozen artifacts only, no data or training access."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import threading
from urllib.parse import urlsplit

import joblib
import pandas as pd
from threadpoolctl import threadpool_limits


class Demo:
    def __init__(self, bundle, assets):
        self.bundle, self.assets = Path(bundle), Path(assets)
        self.manifest = json.loads((self.bundle / "manifest.json").read_bytes())
        self.models = {}
        self.lock = threading.Lock()
        for mode, system in self.manifest["systems"].items():
            name = system["artifact"]
            if Path(name).name != name or not name.endswith(".joblib"):
                raise ValueError("Invalid model artifact path")
            path = self.bundle / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != system["model_sha256"]:
                raise ValueError("Frozen model hash mismatch; rebuild the verified demo bundle")
            self.models[mode] = joblib.load(path)

    def validate(self, payload):
        if not isinstance(payload, dict) or set(payload) != {"mode", "inputs"}:
            raise ValueError("Send a mode and its inputs")
        mode, values = payload["mode"], payload["inputs"]
        if not isinstance(mode, str) or mode not in self.manifest["systems"]:
            raise ValueError("Choose a supported input mode")
        features = self.manifest["systems"][mode]["input_columns"]
        if not isinstance(values, dict) or set(values) != set(features):
            raise ValueError("Supply exactly the fields required by this mode; missing sensors are not filled with zero")
        clean = {}
        for name in features:
            value, schema = values[name], self.manifest["fields"][name]
            if "categories" in schema:
                if not isinstance(value, str) or value not in schema["categories"]:
                    raise ValueError(f"{schema['label']}: choose a recorded category")
            else:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"{schema['label']}: enter a finite number")
                if schema["integer"] and value != int(value):
                    raise ValueError(f"{schema['label']}: enter a whole number, as recorded in the benchmark")
                if not schema["min"] <= value <= schema["max"]:
                    raise ValueError(f"{schema['label']}: use {schema['min']:g}–{schema['max']:g} {schema['unit']} (development range)")
            clean[name] = value
        return mode, clean

    def predict(self, payload):
        mode, values = self.validate(payload)
        system = self.manifest["systems"][mode]
        X = pd.DataFrame([values], columns=system["input_columns"])
        with self.lock, threadpool_limits(limits=1):
            prediction = float(self.models[mode].predict(X)[0])
        if not math.isfinite(prediction):
            raise ValueError("Model returned a nonfinite estimate")
        q = system["threshold"]
        duration = values["Duration"]
        group = next(row for row in system["duration_groups"]
                     if int(row["group"].split("-")[0]) <= duration <= int(row["group"].split("-")[1]))
        return {"mode": mode, "model": system["name"], "prediction": prediction,
                "lower": prediction-q, "upper": prediction+q, "nominal_coverage": .9,
                "test_mae": system["test_mae"], "test_coverage": system["test_coverage"],
                "duration_group": group, "negative_lower_bound": prediction-q < 0,
                "input_fields": system["input_columns"]}

    def __call__(self, environ, start_response):
        def respond(status, value, mime="application/json; charset=utf-8"):
            body = json.dumps(value, allow_nan=False).encode() if isinstance(value, dict) else value
            headers = [("Content-Type", mime), ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
                ("Referrer-Policy", "no-referrer"),
                ("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'self' https://huggingface.co https://*.hf.space")]
            start_response(status, headers)
            return [body]
        path, method = environ.get("PATH_INFO", "/"), environ.get("REQUEST_METHOD", "GET")
        if method == "GET":
            if path == "/api/health":
                return respond("200 OK", {"status": "ready", "models_loaded": len(self.models)})
            if path == "/api/meta":
                return respond("200 OK", self.manifest)
            files = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                     "/style.css": ("style.css", "text/css; charset=utf-8")}
            if path in files:
                name, mime = files[path]
                return respond("200 OK", (self.assets/name).read_bytes(), mime)
            return respond("404 Not Found", {"error": "Not found"})
        if method != "POST" or path != "/api/predict":
            return respond("405 Method Not Allowed", {"error": "Method not allowed"})
        origin = environ.get("HTTP_ORIGIN")
        if origin and urlsplit(origin).netloc != environ.get("HTTP_HOST"):
            return respond("403 Forbidden", {"error": "Use the app's own prediction form"})
        if environ.get("CONTENT_TYPE", "").split(";")[0] != "application/json":
            return respond("415 Unsupported Media Type", {"error": "Expected JSON"})
        try:
            size = int(environ.get("CONTENT_LENGTH", "0"))
            if not 0 < size <= 8192:
                return respond("413 Content Too Large", {"error": "Request must be between 1 and 8192 bytes"})
            payload = json.loads(environ["wsgi.input"].read(size))
            return respond("200 OK", self.predict(payload))
        except (ValueError, TypeError, UnicodeError) as error:
            return respond("400 Bad Request", {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    from waitress import serve
    app = Demo(args.bundle, args.assets)
    print(f"Calorie Lab ready: http://{args.host}:{args.port}", flush=True)
    serve(app, host=args.host, port=args.port, threads=4, max_request_body_size=8192,
          channel_timeout=30, connection_limit=50, expose_tracebacks=False)


if __name__ == "__main__":
    main()
