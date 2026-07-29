const apiBase = "/api/v1/media/videos";

const fileInput = document.querySelector("#videoFile");
const dropZone = document.querySelector("#dropZone");
const selectedName = document.querySelector("#selectedName");
const selectedSize = document.querySelector("#selectedSize");
const uploadButton = document.querySelector("#uploadButton");
const clearButton = document.querySelector("#clearButton");
const refreshButton = document.querySelector("#refreshButton");
const uploadStatus = document.querySelector("#uploadStatus");
const uploadError = document.querySelector("#uploadError");
const libraryStatus = document.querySelector("#libraryStatus");
const videoLibrary = document.querySelector("#videoLibrary");
const videoPlayer = document.querySelector("#videoPlayer");
const playbackRate = document.querySelector("#playbackRate");
const previousFrameButton = document.querySelector("#previousFrameButton");
const nextFrameButton = document.querySelector("#nextFrameButton");
const replayTitle = document.querySelector("#replayTitle");
const currentTime = document.querySelector("#currentTime");
const resolution = document.querySelector("#resolution");
const fps = document.querySelector("#fps");
const playbackStatus = document.querySelector("#playbackStatus");
const playbackError = document.querySelector("#playbackError");

let selectedFile = null;
let activeManifest = null;

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatSeconds(value) {
  if (!Number.isFinite(value)) return "-";
  return `${value.toFixed(2)} s`;
}

function setSelectedFile(file) {
  selectedFile = file;
  selectedName.textContent = file ? file.name : "None";
  selectedSize.textContent = file ? formatBytes(file.size) : "-";
  uploadButton.disabled = !file;
  uploadStatus.textContent = file ? "Ready to upload." : "Waiting for a video.";
  uploadError.textContent = "";
}

fileInput.addEventListener("change", () => {
  setSelectedFile(fileInput.files[0] ?? null);
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("is-dragging");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("is-dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("is-dragging");
  const file = event.dataTransfer.files[0] ?? null;
  if (file) {
    fileInput.files = event.dataTransfer.files;
  }
  setSelectedFile(file);
});

dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});

clearButton.addEventListener("click", () => {
  fileInput.value = "";
  setSelectedFile(null);
});

uploadButton.addEventListener("click", async () => {
  if (!selectedFile) return;
  uploadButton.disabled = true;
  uploadStatus.textContent = "Uploading and validating...";
  uploadError.textContent = "";

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const response = await fetch(apiBase, { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message ?? "Upload failed.");
    }
    uploadStatus.textContent = "Upload complete.";
    await loadLibrary(payload.media_id);
  } catch (error) {
    uploadError.textContent = error.message;
    uploadStatus.textContent = "Upload failed.";
  } finally {
    uploadButton.disabled = !selectedFile;
  }
});

refreshButton.addEventListener("click", () => {
  loadLibrary();
});

async function loadLibrary(selectMediaId = null) {
  libraryStatus.textContent = "Loading library...";
  videoLibrary.replaceChildren();
  try {
    const response = await fetch(apiBase);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message ?? "Could not load the library.");
    }
    renderLibrary(payload);
    libraryStatus.textContent = payload.length ? `${payload.length} video(s) available.` : "No videos yet.";
    if (selectMediaId) {
      await loadReplay(selectMediaId);
    }
  } catch (error) {
    libraryStatus.textContent = "Library unavailable.";
    videoLibrary.textContent = "";
    uploadError.textContent = error.message;
  }
}

function renderLibrary(records) {
  videoLibrary.replaceChildren();
  for (const record of records) {
    const row = document.createElement("article");
    row.className = "library-item";

    const title = document.createElement("h3");
    title.textContent = record.display_name;

    const meta = document.createElement("p");
    meta.textContent = [
      new Date(record.created_at).toLocaleString(),
      formatSeconds(record.duration_seconds),
      `${record.width} x ${record.height}`,
      record.fps ? `${record.fps.toFixed(2)} fps` : "FPS unavailable",
      record.status,
    ].join(" | ");

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Replay";
    button.addEventListener("click", () => loadReplay(record.media_id));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "danger";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", () => deleteVideo(record.media_id, record.display_name));

    const actions = document.createElement("div");
    actions.className = "library-actions";
    actions.append(button, deleteButton);

    row.append(title, meta, actions);
    videoLibrary.append(row);
  }
}

async function deleteVideo(mediaId, displayName) {
  const confirmed = window.confirm(`Delete "${displayName}" from the local media library?`);
  if (!confirmed) return;

  libraryStatus.textContent = "Deleting video...";
  try {
    const response = await fetch(`${apiBase}/${mediaId}`, { method: "DELETE" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message ?? "Could not delete the video.");
    }
    if (activeManifest?.media_id === mediaId) {
      clearReplay();
    }
    libraryStatus.textContent = "Video deleted.";
    await loadLibrary();
  } catch (error) {
    libraryStatus.textContent = "Delete failed.";
    uploadError.textContent = error.message;
  }
}

async function loadReplay(mediaId) {
  playbackStatus.textContent = "Loading replay...";
  playbackError.textContent = "";
  try {
    const response = await fetch(`${apiBase}/${mediaId}/replay`);
    const manifest = await response.json();
    if (!response.ok) {
      throw new Error(manifest.error?.message ?? "Could not load replay.");
    }
    activeManifest = manifest;
    videoPlayer.src = manifest.content_url;
    videoPlayer.playbackRate = Number(playbackRate.value);
    replayTitle.textContent = manifest.display_name;
    resolution.textContent = `${manifest.width} x ${manifest.height}`;
    fps.textContent = manifest.fps ? manifest.fps.toFixed(2) : "-";
    previousFrameButton.disabled = !manifest.fps;
    nextFrameButton.disabled = !manifest.fps;
    playbackStatus.textContent = playbackMessage(manifest.browser_playback_status);
    updateCurrentTime();
  } catch (error) {
    playbackError.textContent = error.message;
    playbackStatus.textContent = "Replay unavailable.";
  }
}

function playbackMessage(status) {
  if (status === "supported") return "Ready for browser playback.";
  if (status === "possibly_unsupported") {
    return "Uploaded, but this container or codec may not play in every browser.";
  }
  if (status === "missing") return "The stored video file is missing.";
  return "This video format is not supported for browser replay.";
}

function clearReplay() {
  activeManifest = null;
  videoPlayer.pause();
  videoPlayer.removeAttribute("src");
  videoPlayer.load();
  replayTitle.textContent = "No video selected";
  currentTime.textContent = "0.00 / 0.00 s";
  resolution.textContent = "-";
  fps.textContent = "-";
  previousFrameButton.disabled = true;
  nextFrameButton.disabled = true;
  playbackStatus.textContent = "Select a stored video to replay.";
  playbackError.textContent = "";
}

playbackRate.addEventListener("change", () => {
  videoPlayer.playbackRate = Number(playbackRate.value);
});

videoPlayer.addEventListener("timeupdate", updateCurrentTime);
videoPlayer.addEventListener("loadedmetadata", updateCurrentTime);
videoPlayer.addEventListener("error", () => {
  playbackError.textContent = "The browser could not play this video. Try MP4 or WebM with a browser-supported codec.";
});

function updateCurrentTime() {
  const duration = Number.isFinite(videoPlayer.duration) ? videoPlayer.duration : activeManifest?.duration_seconds ?? 0;
  currentTime.textContent = `${videoPlayer.currentTime.toFixed(2)} / ${duration.toFixed(2)} s`;
}

previousFrameButton.addEventListener("click", () => stepFrame(-1));
nextFrameButton.addEventListener("click", () => stepFrame(1));

function stepFrame(direction) {
  if (!activeManifest?.fps) return;
  const increment = 1 / activeManifest.fps;
  videoPlayer.currentTime = Math.max(0, videoPlayer.currentTime + direction * increment);
}

loadLibrary();
