const generateButton = document.getElementById("generateBtn");
const resultImage = document.getElementById("resultImage");
const progressText = document.getElementById("progressText");
const statusText = document.getElementById("status");

generateButton.addEventListener("click", async () => {
  const prompt = document.getElementById("prompt").value.trim();
  const width = document.getElementById("width").value;
  const height = document.getElementById("height").value;
  const steps = document.getElementById("steps").value;
  const guidance = document.getElementById("guidance").value;

  if (!prompt) {
    alert("Please enter a prompt!");
    return;
  }

  // Reset UI
  progressText.textContent = "Generating... 0%";
  statusText.textContent = "";
  resultImage.style.opacity = "0.5";

  let progress = 0;
  const interval = setInterval(() => {
    progress = Math.min(progress + Math.random() * 7, 90);
    progressText.textContent = `Generating... ${progress.toFixed(0)}%`;
  }, 400);

  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        width,
        height,
        steps,
        guidance_scale: guidance,
      }),
    });

    const data = await response.json();
    clearInterval(interval);
    progressText.textContent = "Finalizing... 100%";

    if (data.status === "ok") {
      setTimeout(() => {
        resultImage.src = data.image_url + `?t=${Date.now()}`;
        resultImage.style.opacity = "1";
        statusText.textContent = "✅ Image generated successfully!";
        progressText.textContent = "";
      }, 1000);
    } else {
      statusText.textContent = "⚠️ " + (data.detail || "Generation failed");
      progressText.textContent = "";
      resultImage.style.opacity = "1";
    }
  } catch (err) {
    clearInterval(interval);
    statusText.textContent = "❌ Error: " + err.message;
    progressText.textContent = "";
    resultImage.style.opacity = "1";
  }
});
