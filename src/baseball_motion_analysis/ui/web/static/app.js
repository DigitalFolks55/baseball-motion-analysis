const apiBase = "/api/v1/media/videos";
const swingVideoAnalysisApiBase = "/api/v1/analysis/swing/video";

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
const motionType = document.querySelector("#motionType");
const unsupportedMotionNotice = document.querySelector("#unsupportedMotionNotice");
const swingSetupPanel = document.querySelector("#swingSetupPanel");
const swingHandedness = document.querySelector("#swingHandedness");
const swingQualityMode = document.querySelector("#swingQualityMode");
const swingPoseMode = document.querySelector("#swingPoseMode");
const poseOverlaySource = document.querySelector("#poseOverlaySource");
const analysisVideoTitle = document.querySelector("#analysisVideoTitle");
const runSwingAnalysisButton = document.querySelector("#runSwingAnalysisButton");
const clearSwingAnalysisButton = document.querySelector("#clearSwingAnalysisButton");
const swingAnalysisStatus = document.querySelector("#swingAnalysisStatus");
const swingAnalysisError = document.querySelector("#swingAnalysisError");
const swingAnalysisSource = document.querySelector("#swingAnalysisSource");
const swingAnalysisResults = document.querySelector("#swingAnalysisResults");
const swingOverallScore = document.querySelector("#swingOverallScore");
const swingConfidence = document.querySelector("#swingConfidence");
const swingSummary = document.querySelector("#swingSummary");
const swingGoodPoints = document.querySelector("#swingGoodPoints");
const swingImprovementPoints = document.querySelector("#swingImprovementPoints");
const swingDrills = document.querySelector("#swingDrills");
const swingLimitations = document.querySelector("#swingLimitations");
const swingEvents = document.querySelector("#swingEvents");
const swingPoseQuality = document.querySelector("#swingPoseQuality");
const swingPhaseScores = document.querySelector("#swingPhaseScores");
const swingMetrics = document.querySelector("#swingMetrics");
const swingFaults = document.querySelector("#swingFaults");
const poseOverlayCanvas = document.querySelector("#poseOverlayCanvas");
const poseOverlayStatus = document.querySelector("#poseOverlayStatus");

let selectedFile = null;
let activeManifest = null;
let analysisOverlayFrames = [];
let analysisRawOverlayFrames = [];
let analysisEvents = [];

const skeletonLines = [
  ["left_shoulder", "right_shoulder"],
  ["left_hip", "right_hip"],
  ["left_shoulder", "left_hip"],
  ["right_shoulder", "right_hip"],
  ["left_hip", "left_knee"],
  ["right_hip", "right_knee"],
  ["left_knee", "left_ankle"],
  ["right_knee", "right_ankle"],
  ["left_shoulder", "left_elbow"],
  ["left_elbow", "left_wrist"],
  ["right_shoulder", "right_elbow"],
  ["right_elbow", "right_wrist"],
  ["left_wrist", "bat_tip"],
  ["right_wrist", "bat_tip"],
];

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

function formatNumber(value, digits = 2) {
  if (!Number.isFinite(value)) return "-";
  return value.toFixed(digits);
}

function formatLabel(value) {
  if (value === "notebook_parity") return "Single Pose";
  return String(value ?? "-")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
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
    analysisVideoTitle.textContent = manifest.display_name;
    swingAnalysisSource.textContent = manifest.display_name;
    resolution.textContent = `${manifest.width} x ${manifest.height}`;
    fps.textContent = manifest.fps ? manifest.fps.toFixed(2) : "-";
    previousFrameButton.disabled = !manifest.fps;
    nextFrameButton.disabled = !manifest.fps;
    playbackStatus.textContent = playbackMessage(manifest.browser_playback_status);
    clearAnalysis({ status: "Ready to run swing analysis for the selected video." });
    updateCurrentTime();
    updateSwingRunState();
    drawPoseOverlay();
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
  analysisVideoTitle.textContent = "No video selected";
  swingAnalysisSource.textContent = "No video selected";
  currentTime.textContent = "0.00 / 0.00 s";
  resolution.textContent = "-";
  fps.textContent = "-";
  previousFrameButton.disabled = true;
  nextFrameButton.disabled = true;
  playbackStatus.textContent = "Select a stored video to replay.";
  playbackError.textContent = "";
  clearAnalysis({ status: "Select a stored video to run swing analysis." });
  updateSwingRunState();
  drawPoseOverlay();
}

function updateSwingRunState() {
  runSwingAnalysisButton.disabled = motionType.value !== "swing" || !activeManifest;
}

motionType.addEventListener("change", () => {
  const isSwing = motionType.value === "swing";
  swingSetupPanel.hidden = !isSwing;
  unsupportedMotionNotice.hidden = isSwing;
  clearAnalysis({
    status: isSwing
      ? activeManifest
        ? "Ready to run swing analysis for the selected video."
        : "Select a stored video to run swing analysis."
      : "Select Swing to run analysis.",
  });
  updateSwingRunState();
  drawPoseOverlay();
});

swingHandedness.addEventListener("change", () => {
  clearAnalysis({
    status: activeManifest
      ? "Ready to run swing analysis for the selected video."
      : "Select a stored video to run swing analysis.",
  });
});

swingQualityMode.addEventListener("change", () => {
  clearAnalysis({
    status: activeManifest
      ? "Ready to run swing analysis for the selected video."
      : "Select a stored video to run swing analysis.",
  });
});

swingPoseMode.addEventListener("change", () => {
  clearAnalysis({
    status: activeManifest
      ? "Ready to run swing analysis for the selected video."
      : "Select a stored video to run swing analysis.",
  });
});

poseOverlaySource.addEventListener("change", () => {
  drawPoseOverlay();
});

clearSwingAnalysisButton.addEventListener("click", () => {
  clearAnalysis({ status: "Analysis cleared." });
  drawPoseOverlay();
});

runSwingAnalysisButton.addEventListener("click", async () => {
  if (motionType.value !== "swing" || !activeManifest) return;
  clearAnalysis({ status: "Sampling frames and tracking MediaPipe body pose..." });
  swingAnalysisError.textContent = "";
  runSwingAnalysisButton.disabled = true;

  try {
    const response = await fetch(swingVideoAnalysisApiBase, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        media_id: activeManifest.media_id,
        handedness: swingHandedness.value,
        sampling: {
          quality_mode: swingQualityMode.value,
        },
        pose_mode: swingPoseMode.value,
        overlay_source: poseOverlaySource.value,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error?.message ?? "Swing analysis failed.");
    }
    renderSwingVideoAnalysis(result);
    swingAnalysisStatus.textContent = result.pose_cache_hit
      ? "Swing analysis complete. Pose cache reused."
      : "Swing analysis complete.";
    poseOverlayStatus.textContent = overlayMessage();
  } catch (error) {
    swingAnalysisError.textContent = error.message;
    swingAnalysisStatus.textContent = "Swing analysis failed.";
  } finally {
    updateSwingRunState();
    drawPoseOverlay();
  }
});

function clearAnalysis({ status }) {
  analysisOverlayFrames = [];
  analysisRawOverlayFrames = [];
  analysisEvents = [];
  swingAnalysisResults.hidden = true;
  swingAnalysisError.textContent = "";
  swingOverallScore.textContent = "-";
  swingConfidence.textContent = "-";
  swingSummary.textContent = "";
  renderList(swingGoodPoints, []);
  renderList(swingImprovementPoints, []);
  renderList(swingDrills, []);
  renderList(swingLimitations, []);
  renderSwingEvents([]);
  renderPoseQuality(null, null);
  renderPhaseScores([]);
  renderMetrics([]);
  renderFaults([]);
  swingAnalysisStatus.textContent = status;
  poseOverlayStatus.textContent = overlayMessage();
}

function renderSwingVideoAnalysis(result) {
  const analysis = result.analysis;
  const feedback = result.feedback;
  const limitations = uniqueValues([...(feedback.limitations ?? []), ...(result.limitations ?? [])]);

  analysisOverlayFrames = result.overlay_frames ?? result.overlay ?? [];
  analysisRawOverlayFrames = result.raw_overlay_frames ?? result.raw_overlay ?? [];
  analysisEvents = result.events ?? [];
  swingOverallScore.textContent = `${formatNumber(analysis.overall_score, 1)}/100`;
  swingConfidence.textContent = formatNumber(analysis.confidence, 2);
  swingSummary.textContent = feedback.summary;
  renderList(swingGoodPoints, feedback.good_points);
  renderList(swingImprovementPoints, feedback.improvement_points);
  renderList(swingDrills, feedback.drills_or_suggestions);
  renderList(swingLimitations, limitations);
  renderSwingEvents(analysisEvents);
  renderPoseQuality(
    result.pose_diagnostics,
    result.sampling_diagnostics,
    result.raw_pose_diagnostics,
    result.pose_debug_diagnostics,
  );
  renderPhaseScores(analysis.phase_scores);
  renderMetrics(analysis.metrics);
  renderFaults(analysis.detected_faults);
  swingAnalysisResults.hidden = false;
  drawPoseOverlay();
}

function uniqueValues(values) {
  return [...new Set(values.filter(Boolean))];
}

function renderList(container, values) {
  container.replaceChildren();
  for (const value of values ?? []) {
    const item = document.createElement("li");
    item.textContent = value;
    container.append(item);
  }
}

function renderSwingEvents(events) {
  swingEvents.replaceChildren();
  for (const event of events ?? []) {
    const item = document.createElement("li");
    item.textContent = `${event.label}: frame ${event.frame_index}, Event confidence ${formatNumber(event.confidence, 2)}, ${formatLabel(event.detection_method)}`;
    swingEvents.append(item);
  }
}

function renderPoseQuality(poseDiagnostics, samplingDiagnostics, rawPoseDiagnostics = null, poseDebugDiagnostics = null) {
  swingPoseQuality.replaceChildren();
  if (!poseDiagnostics && !samplingDiagnostics && !rawPoseDiagnostics && !poseDebugDiagnostics) {
    appendDiagnostic("Sampling", "-");
    appendDiagnostic("Pose Detection", "-");
    appendDiagnostic("Landmark Coverage", "-");
    appendDiagnostic("Phase Quality", "-");
    return;
  }

  if (samplingDiagnostics) {
    appendDiagnostic("Quality Mode", formatLabel(samplingDiagnostics.quality_mode));
    appendDiagnostic("Sampled Frames", `${samplingDiagnostics.sampled_frame_count} / ${samplingDiagnostics.total_frame_count ?? "-"}`);
    appendDiagnostic("Effective FPS", formatNumber(samplingDiagnostics.effective_fps, 2));
    appendDiagnostic("Cap Applied", samplingDiagnostics.cap_applied ? "Yes" : "No");
  }
  if (poseDiagnostics) {
    appendDiagnostic("Pose Detection", `${formatNumber(poseDiagnostics.detected_pose_frame_ratio * 100, 0)}%`);
    appendDiagnostic("Landmark Coverage", `${formatNumber(poseDiagnostics.required_landmark_coverage * 100, 0)}%`);
    appendDiagnostic("Mean Confidence", formatNumber(poseDiagnostics.mean_confidence, 2));
    appendDiagnostic("Min Confidence", formatNumber(poseDiagnostics.min_confidence, 2));
    appendDiagnostic("Smoothed Frames", String(poseDiagnostics.smoothed_frame_count));
    appendDiagnostic("Interpolated Frames", String(poseDiagnostics.interpolated_frame_count));
    appendDiagnostic("Rejected Outliers", String(poseDiagnostics.rejected_outlier_count));
  }
  if (rawPoseDiagnostics) {
    appendDiagnostic("Raw Pose Detection", `${formatNumber(rawPoseDiagnostics.detected_pose_frame_ratio * 100, 0)}%`);
    appendDiagnostic("Raw Landmark Coverage", `${formatNumber(rawPoseDiagnostics.required_landmark_coverage * 100, 0)}%`);
  }
  if (poseDebugDiagnostics) {
    appendDiagnostic("Pose Mode", formatLabel(poseDebugDiagnostics.processing_mode));
    appendDiagnostic("MediaPipe Running Mode", formatLabel(poseDebugDiagnostics.running_mode));
    appendDiagnostic("Requested Poses", String(poseDebugDiagnostics.requested_num_poses));
    appendDiagnostic("Selection Strategy", formatLabel(poseDebugDiagnostics.player_selection_strategy));
    appendDiagnostic("Selected Candidates", (poseDebugDiagnostics.selected_candidate_indexes ?? []).join(", ") || "-");
    appendDiagnostic("Max Stabilization Delta", formatNumber(poseDebugDiagnostics.max_stabilization_delta_ratio, 2));
    appendDiagnostic("Changed Keypoints", String(poseDebugDiagnostics.stabilization_changed_keypoint_count ?? 0));
  }
}

function appendDiagnostic(label, value) {
  const item = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value;
  item.append(term, description);
  swingPoseQuality.append(item);
}

function renderPhaseScores(scores) {
  swingPhaseScores.replaceChildren();
  for (const score of scores ?? []) {
    const row = document.createElement("tr");
    appendCell(row, formatLabel(score.phase));
    appendCell(row, formatNumber(score.score, 1));
    appendCell(row, `${formatNumber(score.weight * 100, 0)}%`);
    appendCell(row, formatNumber(score.confidence, 2));
    swingPhaseScores.append(row);
  }
}

function renderMetrics(metrics) {
  swingMetrics.replaceChildren();
  for (const metric of metrics ?? []) {
    const row = document.createElement("tr");
    appendCell(row, formatLabel(metric.name));
    appendCell(row, metric.value === null ? "-" : formatNumber(metric.value, 2));
    appendCell(row, formatTarget(metric.target_min, metric.target_max));
    appendCell(row, formatLabel(metric.severity));
    appendCell(row, formatNumber(metric.deduction, 2));
    appendCell(row, (metric.evidence_frames ?? []).join(", "));
    swingMetrics.append(row);
  }
}

function renderFaults(faults) {
  swingFaults.replaceChildren();
  if (!faults?.length) {
    const empty = document.createElement("p");
    empty.textContent = "No detected faults.";
    swingFaults.append(empty);
    return;
  }

  const list = document.createElement("ul");
  for (const fault of faults) {
    const item = document.createElement("li");
    item.textContent = `${formatLabel(fault.fault_type)} at ${formatLabel(fault.phase)} (${formatLabel(fault.severity)}): ${fault.evidence} Evidence frames: ${(fault.evidence_frames ?? []).join(", ")}.`;
    list.append(item);
  }
  swingFaults.append(list);
}

function appendCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  row.append(cell);
}

function formatTarget(min, max) {
  if (min === null && max === null) return "-";
  if (max === null) return `>= ${formatNumber(min, 2)}`;
  if (min === null) return `<= ${formatNumber(max, 2)}`;
  return `${formatNumber(min, 2)} - ${formatNumber(max, 2)}`;
}

function nearestOverlayFrame() {
  const frames = currentOverlayFrames();
  if (!frames.length) return null;
  const fpsValue = activeManifest?.fps;
  if (!fpsValue) return frames[0];
  const currentFrameIndex = Math.round(videoPlayer.currentTime * fpsValue);
  return frames.reduce((nearest, frame) => {
    const nearestDistance = Math.abs((nearest.frame_index ?? 0) - currentFrameIndex);
    const frameDistance = Math.abs((frame.frame_index ?? 0) - currentFrameIndex);
    return frameDistance < nearestDistance ? frame : nearest;
  }, frames[0]);
}

function currentOverlayFrames() {
  if (poseOverlaySource.value === "raw" && analysisRawOverlayFrames.length) {
    return analysisRawOverlayFrames;
  }
  return analysisOverlayFrames;
}

function drawPoseOverlay() {
  const canvas = poseOverlayCanvas;
  const context = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width));
  const height = Math.max(1, Math.round(rect.height));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  context.clearRect(0, 0, canvas.width, canvas.height);

  const frame = nearestOverlayFrame();
  if (!frame?.keypoints?.length) {
    poseOverlayStatus.textContent = overlayMessage();
    return;
  }

  const keypoints = Object.fromEntries(frame.keypoints.map((keypoint) => [keypoint.name, keypoint]));
  const contentRect = videoContentRect(canvas.width, canvas.height);
  drawSkeletonLines(context, keypoints, contentRect);
  for (const keypoint of frame.keypoints) {
    drawKeypoint(context, keypoint, contentRect, frame.is_event_frame);
  }
  if (frame.is_event_frame) {
    drawEventLabel(context, frame, canvas.width);
  }
  poseOverlayStatus.textContent = `${overlayMessage()} Showing ${overlayFrameMatchStatus(frame)} ${frame.source ?? poseOverlaySource.value} pose frame ${frame.frame_index}.`;
}

function overlayFrameMatchStatus(frame) {
  const hasInterpolatedLandmarks = frame.keypoints.some((keypoint) => keypoint.interpolated);
  const fpsValue = activeManifest?.fps;
  const frameTime = Number.isFinite(frame.timestamp_seconds) ? frame.timestamp_seconds : null;
  const offsetMs = frameTime === null ? null : Math.round((frameTime - videoPlayer.currentTime) * 1000);
  const offsetText = offsetMs === null || offsetMs === 0 ? "" : `, offset ${offsetMs} ms`;
  if (hasInterpolatedLandmarks) return `interpolated${offsetText}`;
  if (!fpsValue) return `nearest sampled${offsetText}`;
  const currentFrameIndex = Math.round(videoPlayer.currentTime * fpsValue);
  return currentFrameIndex === frame.frame_index ? "exact sampled" : `nearest sampled${offsetText}`;
}

function drawSkeletonLines(context, keypoints, contentRect) {
  context.save();
  context.strokeStyle = "rgba(255, 255, 255, 0.78)";
  context.lineWidth = 2;
  for (const [startName, endName] of skeletonLines) {
    const start = keypoints[startName];
    const end = keypoints[endName];
    if (!start || !end || start.confidence < 0.1 || end.confidence < 0.1) continue;
    const startPoint = overlayPoint(start, contentRect);
    const endPoint = overlayPoint(end, contentRect);
    context.beginPath();
    context.moveTo(startPoint.x, startPoint.y);
    context.lineTo(endPoint.x, endPoint.y);
    context.stroke();
  }
  context.restore();
}

function drawKeypoint(context, keypoint, contentRect, isEventFrame) {
  const point = overlayPoint(keypoint, contentRect);
  const isBatPoint = keypoint.category === "bat";
  const isLowConfidence = keypoint.category === "low_confidence" || keypoint.confidence < 0.35;
  const radius = isBatPoint ? 5 : 4;
  context.save();
  context.fillStyle = isLowConfidence ? "#d0d5dd" : isBatPoint ? "#f5b301" : "#16a1d9";
  context.strokeStyle = isEventFrame ? "#ff4d4f" : "#ffffff";
  context.lineWidth = isEventFrame ? 3 : 1.5;
  context.beginPath();
  context.arc(point.x, point.y, radius, 0, Math.PI * 2);
  context.fill();
  context.stroke();
  if (keypoint.label && isEventFrame) {
    drawKeypointLabel(context, keypoint.label, point.x, point.y);
  }
  context.restore();
}

function drawKeypointLabel(context, label, x, y) {
  context.font = "600 12px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  context.textBaseline = "bottom";
  const textWidth = context.measureText(label).width;
  const labelX = clamp(x + 7, 2, poseOverlayCanvas.width - textWidth - 8);
  const labelY = clamp(y - 5, 14, poseOverlayCanvas.height - 2);
  context.fillStyle = "rgba(15, 23, 32, 0.76)";
  context.fillRect(labelX - 3, labelY - 14, textWidth + 6, 16);
  context.fillStyle = "#ffffff";
  context.fillText(label, labelX, labelY);
}

function drawEventLabel(context, frame, width) {
  const event = analysisEvents.find((item) => item.frame_index === frame.frame_index);
  if (!event) return;
  context.save();
  context.font = "700 13px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  const label = event.label;
  const textWidth = context.measureText(label).width;
  context.fillStyle = "rgba(255, 77, 79, 0.9)";
  context.fillRect(8, 8, Math.min(width - 16, textWidth + 16), 24);
  context.fillStyle = "#ffffff";
  context.fillText(label, 16, 25);
  context.restore();
}

function videoContentRect(canvasWidth, canvasHeight) {
  const intrinsicWidth = videoPlayer.videoWidth || activeManifest?.width || canvasWidth;
  const intrinsicHeight = videoPlayer.videoHeight || activeManifest?.height || canvasHeight;
  const videoAspect = intrinsicWidth / intrinsicHeight;
  const canvasAspect = canvasWidth / canvasHeight;
  if (!Number.isFinite(videoAspect) || videoAspect <= 0) {
    return { x: 0, y: 0, width: canvasWidth, height: canvasHeight };
  }
  if (canvasAspect > videoAspect) {
    const contentWidth = canvasHeight * videoAspect;
    return {
      x: (canvasWidth - contentWidth) / 2,
      y: 0,
      width: contentWidth,
      height: canvasHeight,
    };
  }
  const contentHeight = canvasWidth / videoAspect;
  return {
    x: 0,
    y: (canvasHeight - contentHeight) / 2,
    width: canvasWidth,
    height: contentHeight,
  };
}

function overlayPoint(keypoint, contentRect) {
  const x = contentRect.x + clamp(Number(keypoint.x), 0, 1) * contentRect.width;
  const y = contentRect.y + clamp(Number(keypoint.y), 0, 1) * contentRect.height;
  return { x, y };
}

function clamp(value, min, max) {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function overlayMessage() {
  if (!activeManifest) return "Overlay hidden: select a stored video.";
  if (!currentOverlayFrames().length) return "Overlay hidden: run swing analysis to detect pose.";
  return "Pose overlay active: sampled key motion points are aligned to replay.";
}

playbackRate.addEventListener("change", () => {
  videoPlayer.playbackRate = Number(playbackRate.value);
});

videoPlayer.addEventListener("timeupdate", () => {
  updateCurrentTime();
  drawPoseOverlay();
});
videoPlayer.addEventListener("loadedmetadata", () => {
  updateCurrentTime();
  drawPoseOverlay();
});
videoPlayer.addEventListener("error", () => {
  playbackError.textContent = "The browser could not play this video. Try MP4 or WebM with a browser-supported codec.";
});
window.addEventListener("resize", drawPoseOverlay);

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
  drawPoseOverlay();
}

loadLibrary();
clearAnalysis({ status: "Select a stored video to run swing analysis." });
updateSwingRunState();
