import os
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, url_for
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_ID = os.getenv("MODEL_ID", "runwayml/stable-diffusion-v1-5")

# Directories
BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "static" / "generated"




GENERATED_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB limit

USE_DIFFUSERS = False
pipeline = None

# Try to load Stable Diffusion
try:
    import torch
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Torch device: {device}")
    print("[INFO] Loading Stable Diffusion pipeline...")

    pipeline = StableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        use_auth_token=HF_TOKEN if HF_TOKEN else None,
        torch_dtype=torch.float16 if device == "cuda" else None,
    )

    pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config)
    pipeline.safety_checker = None
    pipeline.enable_attention_slicing()
    pipeline = pipeline.to(device)

    USE_DIFFUSERS = True
    print("[INFO] Pipeline loaded successfully.")

except Exception as e:
    print("[WARN] Could not initialize local diffusers pipeline:", e)
    USE_DIFFUSERS = False
    pipeline = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"status": "error", "detail": "Invalid JSON"}), 400

    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"status": "error", "detail": "Prompt required"}), 400

    # Parameters
    try:
        steps = int(data.get("steps", 10))
        steps = max(1, min(steps, 150))
    except Exception:
        steps = 10

    try:
        width = int(data.get("width", 400))
        height = int(data.get("height", 400))
        width = max(256, min(width, 1024))
        height = max(256, min(height, 1024))
    except Exception:
        width, height = 400, 400

    try:
        guidance_scale = float(data.get("guidance_scale", 7.5))
    except Exception:
        guidance_scale = 7.5

    negative_prompt = data.get("negative_prompt", None)

    if not USE_DIFFUSERS or pipeline is None:
        return jsonify({
            "status": "error",
            "detail": "Generation backend not available. Please install diffusers & torch properly."
        }), 500

    # Generate image
    try:
        import torch
        gen = None
        if torch.cuda.is_available():
            gen = torch.Generator(device="cuda").manual_seed(torch.randint(0, 2**30, (1,)).item())

        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            height=height,
            width=width,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=gen,
        )

        image = result.images[0]

        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
        save_path = GENERATED_DIR / filename
        image.save(save_path)

        image_url = url_for("static", filename=f"generated/{filename}")
        return jsonify({"status": "ok", "image_url": image_url, "filename": filename})

    except Exception as e:
        return jsonify({"status": "error", "detail": f"Generation failed: {e}"}), 500


@app.route("/gallery")
def gallery():
    files = sorted(GENERATED_DIR.glob("*.png"), reverse=True)
    urls = [url_for("static", filename=f"generated/{p.name}") for p in files]
    return jsonify({"images": urls})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)
