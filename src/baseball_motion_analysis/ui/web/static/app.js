const apiBase = "/api/v1/media/videos";
const swingVideoAnalysisApiBase = "/api/v1/analysis/swing/video";

const languageSelect = document.querySelector("#languageSelect");
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
const poseOverlayToggle = document.querySelector("#poseOverlayToggle");
const evaluationLinesToggle = document.querySelector("#evaluationLinesToggle");
const evaluationMetricToggle = document.querySelector("#evaluationMetricToggle");
const evaluationMetricMenu = document.querySelector("#evaluationMetricMenu");
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
const swingMethodology = document.querySelector("#swingMethodology");
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
let analysisEvaluationOverlay = [];
let poseOverlayEnabled = false;
let evaluationLinesEnabled = false;
let lastSwingAnalysisResult = null;
let lastLibraryRecords = [];

const languageStorageKey = "baseball_motion_analysis.ui_language";
let currentLanguage = supportedLanguage(localStorage.getItem(languageStorageKey) ?? "en");

const allEvaluationMetricsValue = "__all__";
const estimatedImpactPolicy = "body_pose_estimated";
const selectedEvaluationMetrics = new Set();

const translations = {
  en: {
    "app.subtitle": "Baseball Motion Video Review",
    "language.label": "Language",
    "upload.title": "Upload Video",
    "upload.max": "Max {maxUploadMb} MB",
    "upload.choose": "Choose a video or drop it here",
    "upload.format_note": "MP4 and WebM are the most reliable browser replay formats.",
    "upload.button": "Upload",
    "library.title": "Video Library",
    "library.refresh": "Refresh",
    "replay.title": "Replay",
    "replay.speed": "Speed",
    "replay.previous_frame": "Previous Frame",
    "replay.next_frame": "Next Frame",
    "overlay.poses": "Poses",
    "overlay.evaluation_lines": "Evaluation Lines",
    "overlay.metric": "Metric",
    "overlay.all_metrics": "All metrics",
    "analysis.title": "Motion Analysis",
    "analysis.video_driven": "Video-driven",
    "analysis.motion_type": "Motion Type",
    "analysis.motion_help":
      "Swing is runnable now. Throwing, pitching, and fielding are planned analysis categories.",
    "analysis.unsupported_motion":
      "This motion type is planned but not implemented yet. Select Swing to run analysis.",
    "analysis.selected_video": "Selected Video",
    "analysis.pose": "Pose",
    "analysis.pose_description":
      "Detected locally from sampled video frames with MediaPipe body landmarks.",
    "analysis.events": "Events",
    "analysis.events_description":
      "Setup, stride, foot strike, impact, and follow-through are selected automatically.",
    "swing.title": "Swing Analysis",
    "swing.note":
      "Runs from the selected stored video. The app samples frames, tracks player body pose with MediaPipe, detects swing events, and scores the motion.",
    "swing.handedness": "Handedness",
    "swing.handedness_help":
      "Right-handed uses the left side as lead side; left-handed uses the right side. Unknown lowers confidence because a default side interpretation is used.",
    "swing.quality_mode": "Quality Mode",
    "swing.quality_help":
      "Higher accuracy samples more frames for fast swings. Faster mode reduces local runtime but can miss foot strike or estimated impact cues.",
    "swing.advanced_pose_debug": "Advanced Pose Debug",
    "swing.pose_mode": "Pose Mode",
    "swing.pose_mode_help": "Single pose uses raw single-pose MediaPipe landmarks without temporal stabilization.",
    "swing.overlay_source": "Overlay Source",
    "swing.overlay_source_help": "Raw overlay helps compare detector output with the stabilized analysis pose.",
    "swing.run": "Run Swing Analysis",
    "swing.clear_analysis": "Clear Analysis",
    "swing.run_help":
      "Run samples the selected video, tracks MediaPipe body pose locally, detects swing events, and returns in-memory results. Clear removes results and overlays without deleting media.",
    "result.overall": "Overall",
    "result.confidence": "Confidence",
    "result.confidence_help":
      "Confidence reflects visible keypoint quality, handedness certainty, and phase detection certainty.",
    "result.methodology": "Methodology",
    "result.feedback": "Feedback",
    "result.good_points": "Good Points",
    "result.improvement_points": "Improvement Points",
    "result.drills": "Drills",
    "result.events_scores": "Detected Events And Phase Scores",
    "result.metrics": "Metrics",
    "result.detected_faults": "Detected Faults",
    "result.diagnostics": "Diagnostics",
    "result.limitations": "Limitations",
    "result.limitations_help":
      "Limitations identify sampling limits, missing keypoints, weak bat evidence, or 2D camera constraints.",
    "result.pose_quality": "Pose Quality",
    "table.phase": "Phase",
    "table.score": "Score",
    "table.weight": "Weight",
    "table.score_confidence": "Score Confidence",
    "table.metric": "Metric",
    "table.value": "Value",
    "table.unit": "Unit",
    "table.target": "Target",
    "table.severity": "Severity",
    "table.deduction": "Deduction",
    "table.evidence": "Evidence",
    "common.clear": "Clear",
    "common.selected": "Selected",
    "common.size": "Size",
    "common.title": "Title",
    "common.time": "Time",
    "common.resolution": "Resolution",
    "common.none": "None",
    "common.unknown": "Unknown",
    "motion.swing": "Swing",
    "motion.throwing": "Throwing",
    "motion.pitching": "Pitching",
    "motion.fielding": "Fielding",
    "handedness.right_handed": "Right-handed",
    "handedness.left_handed": "Left-handed",
    "quality.higher_accuracy": "Higher accuracy",
    "quality.balanced": "Balanced",
    "quality.faster": "Faster",
    "pose_mode.normal": "Normal",
    "pose_mode.single_pose": "Single pose",
    "overlay_source.stabilized": "Stabilized",
    "overlay_source.raw": "Raw",
    "status.waiting_video": "Waiting for a video.",
    "status.ready_upload": "Ready to upload.",
    "status.uploading": "Uploading and validating...",
    "status.upload_complete": "Upload complete.",
    "status.upload_failed": "Upload failed.",
    "status.library_loading": "Loading library...",
    "status.library_count": "{count} video(s) available.",
    "status.library_empty": "No videos yet.",
    "status.library_unavailable": "Library unavailable.",
    "status.deleting": "Deleting video...",
    "status.deleted": "Video deleted.",
    "status.delete_failed": "Delete failed.",
    "status.replay_loading": "Loading replay...",
    "status.replay_unavailable": "Replay unavailable.",
    "status.ready_analysis": "Ready to run swing analysis for the selected video.",
    "status.select_analysis_video": "Select a stored video to run swing analysis.",
    "status.select_replay_video": "Select a stored video to replay.",
    "status.select_swing": "Select Swing to run analysis.",
    "status.analysis_cleared": "Analysis cleared.",
    "status.analysis_running": "Sampling frames and tracking MediaPipe body pose...",
    "status.analysis_complete": "Swing analysis complete.",
    "status.analysis_cache_complete": "Swing analysis complete. Pose cache reused.",
    "status.analysis_failed": "Swing analysis failed.",
    "status.no_video_selected": "No video selected",
    "status.browser_supported": "Ready for browser playback.",
    "status.browser_possibly_unsupported":
      "Uploaded, but this container or codec may not play in every browser.",
    "status.video_missing": "The stored video file is missing.",
    "status.browser_unsupported": "This video format is not supported for browser replay.",
    "status.video_error": "The browser could not play this video. Try MP4 or WebM with a browser-supported codec.",
    "overlay.hidden_select": "Overlay hidden: select a stored video.",
    "overlay.hidden_run": "Overlay hidden: run swing analysis to detect pose.",
    "overlay.hidden_off": "Overlay hidden: poses and evaluation lines are off.",
    "overlay.active": "Overlay active: {modes} aligned to replay.",
    "overlay.showing": "{message} Showing {matchStatus} {source} pose frame {frameIndex}.",
    "overlay.poses_mode": "poses",
    "overlay.evaluation_lines_mode": "evaluation lines",
    "overlay.metric_lines_mode": "{metricLabel} lines",
    "overlay.metric_groups_mode": "{count} metric groups",
    "overlay.interpolated": "interpolated{offset}",
    "overlay.nearest_sampled": "nearest sampled{offset}",
    "overlay.exact_sampled": "exact sampled",
    "overlay.offset": ", offset {offsetMs} ms",
    "result.summary":
      "Based on the visible frames, the v2 youth baseline swing evaluation scored this swing {score}/100. The result confidence is {confidence}.",
    "result.no_faults": "No detected faults.",
    "result.event_row": "{label}: frame {frameIndex}, Event confidence {confidence}, {method}",
    "result.event_fallback": "Fallback",
    "result.event_status": "Status",
    "result.fault_row": "{faultType} at {phase} ({severity}):",
    "result.fault_evidence": "{evidence} Evidence frames: {frames}.",
    "confirm.delete": "Delete \"{displayName}\" from the local media library?",
  },
  ja: {
    "app.subtitle": "野球動作ビデオレビュー",
    "language.label": "言語",
    "upload.title": "動画アップロード",
    "upload.max": "最大 {maxUploadMb} MB",
    "upload.choose": "動画を選択するか、ここにドロップ",
    "upload.format_note": "ブラウザ再生は MP4 と WebM がもっとも安定しています。",
    "upload.button": "アップロード",
    "library.title": "動画ライブラリ",
    "library.refresh": "更新",
    "replay.title": "再生",
    "replay.speed": "速度",
    "replay.previous_frame": "前のフレーム",
    "replay.next_frame": "次のフレーム",
    "overlay.poses": "姿勢",
    "overlay.evaluation_lines": "評価線",
    "overlay.metric": "指標",
    "overlay.all_metrics": "すべての指標",
    "analysis.title": "動作分析",
    "analysis.video_driven": "動画ベース",
    "analysis.motion_type": "動作タイプ",
    "analysis.motion_help": "現在実行できる分析はスイングです。送球、投球、守備は予定カテゴリです。",
    "analysis.unsupported_motion": "この動作タイプは予定中で、まだ実装されていません。分析するにはスイングを選択してください。",
    "analysis.selected_video": "選択中の動画",
    "analysis.pose": "姿勢",
    "analysis.pose_description": "サンプリングした動画フレームから MediaPipe の身体ランドマークでローカル検出します。",
    "analysis.events": "イベント",
    "analysis.events_description": "構え、ストライド、足の着地、インパクト、フォロースルーを自動選択します。",
    "swing.title": "スイング分析",
    "swing.note": "選択した保存済み動画から実行します。フレームをサンプリングし、MediaPipe で身体姿勢を追跡し、スイングイベントを検出して採点します。",
    "swing.handedness": "打席",
    "swing.handedness_help": "右打ちは左側をリード側、左打ちは右側をリード側として扱います。不明の場合は標準解釈を使うため信頼度が下がります。",
    "swing.quality_mode": "品質モード",
    "swing.quality_help": "高精度は速いスイング向けに多くのフレームをサンプリングします。高速は処理時間を短縮しますが、足の着地や推定インパクトを見落とす場合があります。",
    "swing.advanced_pose_debug": "詳細な姿勢デバッグ",
    "swing.pose_mode": "姿勢モード",
    "swing.pose_mode_help": "単一姿勢は時間方向の安定化なしで MediaPipe の生ランドマークを使います。",
    "swing.overlay_source": "オーバーレイ元",
    "swing.overlay_source_help": "Raw 表示は検出器の出力と安定化後の分析姿勢を比較するために使います。",
    "swing.run": "スイング分析を実行",
    "swing.clear_analysis": "分析をクリア",
    "swing.run_help": "実行すると選択動画をサンプリングし、MediaPipe の身体姿勢をローカルで追跡し、スイングイベントを検出してメモリ上の結果を返します。クリアはメディアを削除せず結果とオーバーレイだけを消します。",
    "result.overall": "総合",
    "result.confidence": "信頼度",
    "result.confidence_help": "信頼度は、見えているキーポイント品質、打席の確かさ、フェーズ検出の確かさを反映します。",
    "result.methodology": "評価方式",
    "result.feedback": "フィードバック",
    "result.good_points": "良い点",
    "result.improvement_points": "改善ポイント",
    "result.drills": "練習メニュー",
    "result.events_scores": "検出イベントとフェーズスコア",
    "result.metrics": "指標",
    "result.detected_faults": "検出された課題",
    "result.diagnostics": "診断情報",
    "result.limitations": "制限事項",
    "result.limitations_help": "制限事項は、サンプリング制限、キーポイント不足、バット情報の弱さ、2Dカメラ制約などを示します。",
    "result.pose_quality": "姿勢品質",
    "table.phase": "フェーズ",
    "table.score": "スコア",
    "table.weight": "重み",
    "table.score_confidence": "スコア信頼度",
    "table.metric": "指標",
    "table.value": "値",
    "table.unit": "単位",
    "table.target": "目標",
    "table.severity": "重要度",
    "table.deduction": "減点",
    "table.evidence": "根拠",
    "common.clear": "クリア",
    "common.selected": "選択",
    "common.size": "サイズ",
    "common.title": "タイトル",
    "common.time": "時間",
    "common.resolution": "解像度",
    "common.none": "なし",
    "common.unknown": "不明",
    "motion.swing": "スイング",
    "motion.throwing": "送球",
    "motion.pitching": "投球",
    "motion.fielding": "守備",
    "handedness.right_handed": "右打ち",
    "handedness.left_handed": "左打ち",
    "quality.higher_accuracy": "高精度",
    "quality.balanced": "バランス",
    "quality.faster": "高速",
    "pose_mode.normal": "通常",
    "pose_mode.single_pose": "単一姿勢",
    "overlay_source.stabilized": "安定化後",
    "overlay_source.raw": "Raw",
    "status.waiting_video": "動画を待機中です。",
    "status.ready_upload": "アップロードできます。",
    "status.uploading": "アップロードして検証中...",
    "status.upload_complete": "アップロードが完了しました。",
    "status.upload_failed": "アップロードに失敗しました。",
    "status.library_loading": "ライブラリを読み込み中...",
    "status.library_count": "{count} 件の動画があります。",
    "status.library_empty": "動画はまだありません。",
    "status.library_unavailable": "ライブラリを利用できません。",
    "status.deleting": "動画を削除中...",
    "status.deleted": "動画を削除しました。",
    "status.delete_failed": "削除に失敗しました。",
    "status.replay_loading": "再生情報を読み込み中...",
    "status.replay_unavailable": "再生できません。",
    "status.ready_analysis": "選択した動画のスイング分析を実行できます。",
    "status.select_analysis_video": "スイング分析を実行する保存済み動画を選択してください。",
    "status.select_replay_video": "再生する保存済み動画を選択してください。",
    "status.select_swing": "分析するにはスイングを選択してください。",
    "status.analysis_cleared": "分析をクリアしました。",
    "status.analysis_running": "フレームをサンプリングし、MediaPipe の身体姿勢を追跡中...",
    "status.analysis_complete": "スイング分析が完了しました。",
    "status.analysis_cache_complete": "スイング分析が完了しました。姿勢キャッシュを再利用しました。",
    "status.analysis_failed": "スイング分析に失敗しました。",
    "status.no_video_selected": "動画未選択",
    "status.browser_supported": "ブラウザで再生できます。",
    "status.browser_possibly_unsupported": "アップロード済みですが、このコンテナまたはコーデックは一部のブラウザで再生できない場合があります。",
    "status.video_missing": "保存済み動画ファイルが見つかりません。",
    "status.browser_unsupported": "この動画形式はブラウザ再生に対応していません。",
    "status.video_error": "ブラウザでこの動画を再生できませんでした。MP4 または WebM の対応コーデックを試してください。",
    "overlay.hidden_select": "オーバーレイ非表示: 保存済み動画を選択してください。",
    "overlay.hidden_run": "オーバーレイ非表示: スイング分析を実行して姿勢を検出してください。",
    "overlay.hidden_off": "オーバーレイ非表示: 姿勢と評価線がオフです。",
    "overlay.active": "オーバーレイ表示中: {modes} を再生に合わせています。",
    "overlay.showing": "{message} {matchStatus} の {source} 姿勢フレーム {frameIndex} を表示中。",
    "overlay.poses_mode": "姿勢",
    "overlay.evaluation_lines_mode": "評価線",
    "overlay.metric_lines_mode": "{metricLabel} の線",
    "overlay.metric_groups_mode": "{count} 個の指標グループ",
    "overlay.interpolated": "補間{offset}",
    "overlay.nearest_sampled": "最寄りサンプル{offset}",
    "overlay.exact_sampled": "一致したサンプル",
    "overlay.offset": "、差分 {offsetMs} ms",
    "result.summary": "表示フレームに基づく v2 少年野球ベースライン評価では、このスイングは {score}/100、結果の信頼度は {confidence} です。",
    "result.no_faults": "検出された課題はありません。",
    "result.event_row": "{label}: フレーム {frameIndex}、イベント信頼度 {confidence}、{method}",
    "result.event_fallback": "フォールバック",
    "result.event_status": "状態",
    "result.fault_row": "{phase} の {faultType}（{severity}）:",
    "result.fault_evidence": "{evidence} 根拠フレーム: {frames}。",
    "confirm.delete": "ローカルメディアライブラリから「{displayName}」を削除しますか？",
  },
};

const localizedLabels = {
  en: {
    metrics: {
      normalized_stance_width: "Stance width",
      torso_forward_tilt: "Torso tilt",
      torso_tilt_preservation: "Tilt hold",
      grip_loading_vector: "Grip load",
      rear_knee_sway: "Rear knee sway",
      head_translation_ratio: "Head drift",
      early_connection_angle: "Connection",
      lead_knee_blocking_index: "Lead block",
      hip_shoulder_separation_timing: "Hip/shoulder timing",
      estimated_attack_angle: "Attack angle",
      follow_through_posture_balance: "Follow-through",
    },
    values: {
      setup: "Setup",
      stride: "Stride",
      foot_strike: "Foot Strike",
      impact: "Impact",
      follow_through: "Follow Through",
      swing_evaluation_v2: "Swing Evaluation V2",
      higher_accuracy: "Higher Accuracy",
      balanced: "Balanced",
      faster: "Faster",
      normal: "Normal",
      notebook_parity: "Single Pose",
      body_pose_estimated: "Body-Pose Estimated",
      skip_without_ball: "Skip Without Ball",
      require_ball_contact: "Require Ball Contact",
      detected: "Detected",
      estimated: "Estimated",
      skipped: "Skipped",
      unavailable: "Unavailable",
      video: "Video",
      raw: "Raw",
      stabilized: "Stabilized",
      good: "Good",
      warning: "Warning",
      severe: "Severe",
      not_evaluated: "Not Evaluated",
      door_swing_casting: "Door Swing / Casting",
      forward_axis_drift_rushing: "Forward Axis Drift / Rushing",
      arms_only_one_piece: "Arms-Only / One-Piece Swing",
      excessive_upper_swing_early_extension: "Excessive Upper Swing / Early Extension",
      collapsed_lead_side: "Collapsed Lead Side",
      fake_candidate_selection: "Fake Candidate Selection",
    },
    diagnostics: {
      quality_mode: "Quality Mode",
      sampled_frames: "Sampled Frames",
      effective_fps: "Effective FPS",
      cap_applied: "Cap Applied",
      pose_detection: "Pose Detection",
      landmark_coverage: "Landmark Coverage",
      mean_confidence: "Mean Confidence",
      min_confidence: "Min Confidence",
      smoothed_frames: "Smoothed Frames",
      interpolated_frames: "Interpolated Frames",
      rejected_outliers: "Rejected Outliers",
      raw_pose_detection: "Raw Pose Detection",
      raw_landmark_coverage: "Raw Landmark Coverage",
      pose_mode: "Pose Mode",
      mediapipe_running_mode: "MediaPipe Running Mode",
      requested_poses: "Requested Poses",
      selection_strategy: "Selection Strategy",
      selected_candidates: "Selected Candidates",
      max_stabilization_delta: "Max Stabilization Delta",
      changed_keypoints: "Changed Keypoints",
      candidate_switches: "Candidate Switches",
      candidate_ambiguity: "Candidate Ambiguity",
      active_window: "Active Window",
      active_window_peak: "Peak Motion Frame",
      frame_quality: "Frame Quality",
      weak_frames: "Weak Frames",
      rejected_frames: "Rejected Frames",
      scoring_evidence: "Scoring Evidence",
      sampling: "Sampling",
      phase_quality: "Phase Quality",
    },
    goodPoints: {
      "Setup stance width matched the baseline.": "Setup stance width matched the baseline.",
      "Setup torso forward tilt matched the baseline.":
        "Setup torso forward tilt matched the baseline.",
      "Torso forward tilt was preserved from setup to impact.":
        "Torso forward tilt was preserved from setup to impact.",
      "Grip loading stayed near the rear-side baseline.": "Grip loading stayed near the rear-side baseline.",
      "Rear knee sway stayed controlled during stride.": "Rear knee sway stayed controlled during stride.",
      "Head movement stayed controlled through impact.": "Head movement stayed controlled through impact.",
      "Lead arm connection stayed in the target range.": "Lead arm connection stayed in the target range.",
      "Lead knee braced or extended from foot strike to impact.":
        "Lead knee braced or extended from foot strike to impact.",
      "Pelvis rotation led shoulder rotation.": "Pelvis rotation led shoulder rotation.",
      "Attack angle stayed near the target range.": "Attack angle stayed near the target range.",
      "Follow-through posture and head position stayed controlled.":
        "Follow-through posture and head position stayed controlled.",
    },
    drills: {
      "Cross-chest rotation drill": "Cross-chest rotation drill",
      "Inside-out tee drill": "Inside-out tee drill",
      "5-second rear leg hold drill": "5-second rear leg hold drill",
      "Single-leg swing drill": "Single-leg swing drill",
      "Hugged-bat lower-body drill": "Hugged-bat lower-body drill",
      "Stationary tee work": "Stationary tee work",
      "High-grip stop drill": "High-grip stop drill",
      "Hoop rotation drill": "Hoop rotation drill",
      "Front-leg stiff-stop drill": "Front-leg stiff-stop drill",
    },
  },
  ja: {
    metrics: {
      normalized_stance_width: "スタンス幅",
      torso_forward_tilt: "体幹前傾",
      torso_tilt_preservation: "前傾維持",
      grip_loading_vector: "グリップの溜め",
      rear_knee_sway: "後ろ膝の流れ",
      head_translation_ratio: "頭の移動",
      early_connection_angle: "リード腕の連動",
      lead_knee_blocking_index: "前膝のブロック",
      hip_shoulder_separation_timing: "骨盤/肩のタイミング",
      estimated_attack_angle: "推定アタック角",
      follow_through_posture_balance: "フォロースルー",
    },
    values: {
      setup: "構え",
      stride: "ストライド",
      foot_strike: "足の着地",
      impact: "インパクト",
      follow_through: "フォロースルー",
      swing_evaluation_v2: "スイング評価 V2",
      higher_accuracy: "高精度",
      balanced: "バランス",
      faster: "高速",
      normal: "通常",
      notebook_parity: "単一姿勢",
      body_pose_estimated: "身体姿勢から推定",
      skip_without_ball: "ボールなしはスキップ",
      require_ball_contact: "ボール接触を必須",
      detected: "検出",
      estimated: "推定",
      skipped: "スキップ",
      unavailable: "利用不可",
      video: "動画",
      raw: "Raw",
      stabilized: "安定化後",
      good: "良好",
      warning: "注意",
      severe: "大きな注意",
      not_evaluated: "未評価",
      door_swing_casting: "ドアスイング / キャスティング",
      forward_axis_drift_rushing: "前方への軸流れ / 突っ込み",
      arms_only_one_piece: "腕だけ / 一体回転",
      excessive_upper_swing_early_extension: "過度なアッパー / 早い伸び上がり",
      collapsed_lead_side: "前側の崩れ",
      fake_candidate_selection: "テスト用候補選択",
    },
    diagnostics: {
      quality_mode: "品質モード",
      sampled_frames: "サンプルフレーム",
      effective_fps: "有効 FPS",
      cap_applied: "上限適用",
      pose_detection: "姿勢検出",
      landmark_coverage: "ランドマーク網羅率",
      mean_confidence: "平均信頼度",
      min_confidence: "最小信頼度",
      smoothed_frames: "平滑化フレーム",
      interpolated_frames: "補間フレーム",
      rejected_outliers: "外れ値除外",
      raw_pose_detection: "Raw 姿勢検出",
      raw_landmark_coverage: "Raw ランドマーク網羅率",
      pose_mode: "姿勢モード",
      mediapipe_running_mode: "MediaPipe 実行モード",
      requested_poses: "要求姿勢数",
      selection_strategy: "選択方式",
      selected_candidates: "選択候補",
      max_stabilization_delta: "最大安定化差分",
      changed_keypoints: "変更キーポイント数",
      candidate_switches: "候補切替",
      candidate_ambiguity: "候補の曖昧さ",
      active_window: "有効スイング区間",
      active_window_peak: "最大動作フレーム",
      frame_quality: "フレーム品質",
      weak_frames: "弱いフレーム",
      rejected_frames: "除外フレーム",
      scoring_evidence: "採点根拠",
      sampling: "サンプリング",
      phase_quality: "フェーズ品質",
    },
    goodPoints: {
      "Setup stance width matched the baseline.": "構えのスタンス幅は評価基準に合っています。",
      "Setup torso forward tilt matched the baseline.":
        "構えの体幹前傾は評価基準ンに合っています。",
      "Torso forward tilt was preserved from setup to impact.":
        "構えからインパクトまで体幹前傾を維持できています。",
      "Grip loading stayed near the rear-side baseline.": "グリップの溜めが後ろ側の基準付近に保たれています。",
      "Rear knee sway stayed controlled during stride.": "ストライド中の後ろ膝の流れが抑えられています。",
      "Head movement stayed controlled through impact.": "インパクトまで頭の動きが抑えられています。",
      "Lead arm connection stayed in the target range.": "リード腕の連動角度が目標範囲に収まっています。",
      "Lead knee braced or extended from foot strike to impact.":
        "足の着地からインパクトにかけて前膝でブロックできています。",
      "Pelvis rotation led shoulder rotation.": "骨盤の回転が肩の回転に先行しています。",
      "Attack angle stayed near the target range.": "アタック角が目標範囲付近に保たれています。",
      "Follow-through posture and head position stayed controlled.":
        "フォロースルーの姿勢と頭の位置が安定しています。",
    },
    drills: {
      "Cross-chest rotation drill": "胸の前で腕を組む回転ドリル",
      "Inside-out tee drill": "インサイドアウト・ティードリル",
      "5-second rear leg hold drill": "後ろ脚5秒キープドリル",
      "Single-leg swing drill": "片脚スイングドリル",
      "Hugged-bat lower-body drill": "バット抱え下半身ドリル",
      "Stationary tee work": "止まった状態でのティー練習",
      "High-grip stop drill": "高いグリップ位置で止めるドリル",
      "Hoop rotation drill": "フープ回転ドリル",
      "Front-leg stiff-stop drill": "前脚ストップドリル",
    },
  },
};

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

function supportedLanguage(language) {
  return language === "ja" ? "ja" : "en";
}

function t(key, params = {}) {
  const template = translations[currentLanguage]?.[key] ?? translations.en[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? ""));
}

function localizedGroup(groupName) {
  return localizedLabels[currentLanguage]?.[groupName] ?? localizedLabels.en[groupName] ?? {};
}

function localizedValue(value) {
  const key = String(value ?? "-");
  return localizedGroup("values")[key] ?? formatTitleCase(key);
}

function localizedDiagnosticLabel(key) {
  return localizedGroup("diagnostics")[key] ?? localizedValue(key);
}

function applyLanguage() {
  document.documentElement.lang = currentLanguage;
  if (languageSelect) languageSelect.value = currentLanguage;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    const params = { maxUploadMb: element.dataset.maxUploadMb ?? "" };
    element.textContent = t(element.dataset.i18n, params);
  }
  updateEvaluationMetricSelect({ preserveSelection: true });
  refreshStaticStateText();
  if (lastSwingAnalysisResult) {
    renderSwingVideoAnalysis(lastSwingAnalysisResult);
  } else {
    poseOverlayStatus.textContent = overlayMessage();
  }
  if (lastLibraryRecords.length) {
    renderLibrary(lastLibraryRecords);
  }
  drawPoseOverlay();
}

function refreshStaticStateText() {
  if (!selectedFile) selectedName.textContent = t("common.none");
  if (!activeManifest) {
    replayTitle.textContent = t("status.no_video_selected");
    analysisVideoTitle.textContent = t("status.no_video_selected");
    swingAnalysisSource.textContent = t("status.no_video_selected");
    playbackStatus.textContent = t("status.select_replay_video");
  }
  if (!lastSwingAnalysisResult) {
    swingAnalysisStatus.textContent = activeManifest
      ? t("status.ready_analysis")
      : t("status.select_analysis_video");
  }
}

languageSelect?.addEventListener("change", () => {
  currentLanguage = supportedLanguage(languageSelect.value);
  localStorage.setItem(languageStorageKey, currentLanguage);
  applyLanguage();
});

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

function formatTitleCase(value) {
  return String(value ?? "-")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatLabel(value) {
  return localizedValue(value);
}

function formatEvaluationMetricLabel(metricName) {
  return localizedGroup("metrics")[metricName] ?? formatLabel(metricName);
}

function setSelectedFile(file) {
  selectedFile = file;
  selectedName.textContent = file ? file.name : t("common.none");
  selectedSize.textContent = file ? formatBytes(file.size) : "-";
  uploadButton.disabled = !file;
  uploadStatus.textContent = file ? t("status.ready_upload") : t("status.waiting_video");
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
  uploadStatus.textContent = t("status.uploading");
  uploadError.textContent = "";

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const response = await fetch(apiBase, { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message ?? "Upload failed.");
    }
    uploadStatus.textContent = t("status.upload_complete");
    await loadLibrary(payload.media_id);
  } catch (error) {
    uploadError.textContent = error.message;
    uploadStatus.textContent = t("status.upload_failed");
  } finally {
    uploadButton.disabled = !selectedFile;
  }
});

refreshButton.addEventListener("click", () => {
  loadLibrary();
});

async function loadLibrary(selectMediaId = null) {
  libraryStatus.textContent = t("status.library_loading");
  videoLibrary.replaceChildren();
  try {
    const response = await fetch(apiBase);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message ?? "Could not load the library.");
    }
    lastLibraryRecords = payload;
    renderLibrary(payload);
    libraryStatus.textContent = payload.length
      ? t("status.library_count", { count: payload.length })
      : t("status.library_empty");
    if (selectMediaId) {
      await loadReplay(selectMediaId);
    }
  } catch (error) {
    libraryStatus.textContent = t("status.library_unavailable");
    lastLibraryRecords = [];
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
    button.textContent = t("replay.title");
    button.addEventListener("click", () => loadReplay(record.media_id));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "danger";
    deleteButton.textContent = currentLanguage === "ja" ? "削除" : "Delete";
    deleteButton.addEventListener("click", () => deleteVideo(record.media_id, record.display_name));

    const actions = document.createElement("div");
    actions.className = "library-actions";
    actions.append(button, deleteButton);

    row.append(title, meta, actions);
    videoLibrary.append(row);
  }
}

async function deleteVideo(mediaId, displayName) {
  const confirmed = window.confirm(t("confirm.delete", { displayName }));
  if (!confirmed) return;

  libraryStatus.textContent = t("status.deleting");
  try {
    const response = await fetch(`${apiBase}/${mediaId}`, { method: "DELETE" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message ?? "Could not delete the video.");
    }
    if (activeManifest?.media_id === mediaId) {
      clearReplay();
    }
    libraryStatus.textContent = t("status.deleted");
    await loadLibrary();
  } catch (error) {
    libraryStatus.textContent = t("status.delete_failed");
    uploadError.textContent = error.message;
  }
}

async function loadReplay(mediaId) {
  playbackStatus.textContent = t("status.replay_loading");
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
    clearAnalysis({ status: t("status.ready_analysis") });
    updateCurrentTime();
    updateSwingRunState();
    drawPoseOverlay();
  } catch (error) {
    playbackError.textContent = error.message;
    playbackStatus.textContent = t("status.replay_unavailable");
  }
}

function playbackMessage(status) {
  if (status === "supported") return t("status.browser_supported");
  if (status === "possibly_unsupported") {
    return t("status.browser_possibly_unsupported");
  }
  if (status === "missing") return t("status.video_missing");
  return t("status.browser_unsupported");
}

function clearReplay() {
  activeManifest = null;
  videoPlayer.pause();
  videoPlayer.removeAttribute("src");
  videoPlayer.load();
  replayTitle.textContent = t("status.no_video_selected");
  analysisVideoTitle.textContent = t("status.no_video_selected");
  swingAnalysisSource.textContent = t("status.no_video_selected");
  currentTime.textContent = "0.00 / 0.00 s";
  resolution.textContent = "-";
  fps.textContent = "-";
  previousFrameButton.disabled = true;
  nextFrameButton.disabled = true;
  playbackStatus.textContent = t("status.select_replay_video");
  playbackError.textContent = "";
  clearAnalysis({ status: t("status.select_analysis_video") });
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
        ? t("status.ready_analysis")
        : t("status.select_analysis_video")
      : t("status.select_swing"),
  });
  updateSwingRunState();
  drawPoseOverlay();
});

swingHandedness.addEventListener("change", () => {
  clearAnalysis({
    status: activeManifest
      ? t("status.ready_analysis")
      : t("status.select_analysis_video"),
  });
});

swingQualityMode.addEventListener("change", () => {
  clearAnalysis({
    status: activeManifest
      ? t("status.ready_analysis")
      : t("status.select_analysis_video"),
  });
});

swingPoseMode.addEventListener("change", () => {
  clearAnalysis({
    status: activeManifest
      ? t("status.ready_analysis")
      : t("status.select_analysis_video"),
  });
});

poseOverlaySource.addEventListener("change", () => {
  drawPoseOverlay();
});

clearSwingAnalysisButton.addEventListener("click", () => {
  clearAnalysis({ status: t("status.analysis_cleared") });
  drawPoseOverlay();
});

runSwingAnalysisButton.addEventListener("click", async () => {
  if (motionType.value !== "swing" || !activeManifest) return;
  clearAnalysis({ status: t("status.analysis_running") });
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
        impact_detection_policy: estimatedImpactPolicy,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error?.message ?? "Swing analysis failed.");
    }
    renderSwingVideoAnalysis(result);
    swingAnalysisStatus.textContent = result.pose_cache_hit
      ? t("status.analysis_cache_complete")
      : t("status.analysis_complete");
    poseOverlayStatus.textContent = overlayMessage();
  } catch (error) {
    swingAnalysisError.textContent = error.message;
    swingAnalysisStatus.textContent = t("status.analysis_failed");
  } finally {
    updateSwingRunState();
    drawPoseOverlay();
  }
});

function clearAnalysis({ status }) {
  lastSwingAnalysisResult = null;
  analysisOverlayFrames = [];
  analysisRawOverlayFrames = [];
  analysisEvents = [];
  analysisEvaluationOverlay = [];
  poseOverlayEnabled = false;
  evaluationLinesEnabled = false;
  selectedEvaluationMetrics.clear();
  updatePoseOverlayToggle();
  updateEvaluationLinesToggle();
  updateEvaluationMetricSelect({ preserveSelection: false });
  swingAnalysisResults.hidden = true;
  swingAnalysisError.textContent = "";
  swingOverallScore.textContent = "-";
  swingConfidence.textContent = "-";
  swingMethodology.textContent = "-";
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
  lastSwingAnalysisResult = result;
  const analysis = result.analysis;
  const feedback = result.feedback;
  const limitations = uniqueValues([...(feedback.limitations ?? []), ...(result.limitations ?? [])]);
  const visibleEvents = (result.events ?? []).filter((event) => event.is_visible !== false);

  analysisOverlayFrames = result.overlay_frames ?? result.overlay ?? [];
  analysisRawOverlayFrames = result.raw_overlay_frames ?? result.raw_overlay ?? [];
  analysisEvents = visibleEvents;
  analysisEvaluationOverlay = result.evaluation_overlay ?? result.evaluation_lines ?? [];
  poseOverlayEnabled = analysisOverlayFrames.length > 0 || analysisRawOverlayFrames.length > 0;
  updatePoseOverlayToggle();
  updateEvaluationLinesToggle();
  updateEvaluationMetricSelect({ preserveSelection: false });
  swingOverallScore.textContent = `${formatNumber(analysis.overall_score, 1)}/100`;
  swingConfidence.textContent = formatNumber(analysis.confidence, 2);
  swingMethodology.textContent = formatLabel(analysis.methodology_version ?? "swing_evaluation_v2");
  swingSummary.textContent = localizedSwingSummary(analysis, feedback);
  renderList(swingGoodPoints, localizedGoodPoints(analysis, feedback));
  renderList(swingImprovementPoints, localizedImprovementPoints(analysis, feedback));
  renderList(swingDrills, localizedDrills(feedback));
  renderList(swingLimitations, localizedLimitations(limitations));
  renderSwingEvents(visibleEvents);
  renderPoseQuality(
    result.pose_diagnostics,
    result.sampling_diagnostics,
    result.raw_pose_diagnostics,
    result.pose_debug_diagnostics,
    result.frame_quality_diagnostics,
    result.active_window_diagnostics,
    result.scoring_evidence_diagnostics,
  );
  renderPhaseScores(analysis.phase_scores);
  renderMetrics(analysis.metrics);
  renderFaults(analysis.detected_faults);
  swingAnalysisResults.hidden = false;
  drawPoseOverlay();
}

function localizedSwingSummary(analysis, feedback) {
  if (currentLanguage === "en") return feedback.summary;
  return t("result.summary", {
    score: formatNumber(analysis.overall_score, 1),
    confidence: formatNumber(analysis.confidence, 2),
  });
}

function localizedGoodPoints(analysis, feedback) {
  if (currentLanguage === "en") return feedback.good_points;
  const goodPointLabels = localizedGroup("goodPoints");
  return (analysis.good_points?.length ? analysis.good_points : feedback.good_points ?? []).map(
    (point) => goodPointLabels[point] ?? point,
  );
}

function localizedImprovementPoints(analysis, feedback) {
  if (currentLanguage === "en") return feedback.improvement_points;
  if (analysis.detected_faults?.length) {
    return analysis.detected_faults.map((fault) => localizedFaultFeedback(fault));
  }
  const weakMetrics = (analysis.metrics ?? []).filter((metric) =>
    ["warning", "severe"].includes(metric.severity),
  );
  if (weakMetrics.length) {
    return weakMetrics.map(
      (metric) =>
        `${formatEvaluationMetricLabel(metric.name)} に注意が必要な可能性があります。測定値: ${
          metric.value === null ? "-" : formatNumber(metric.value, 2)
        }。`,
    );
  }
  return ["利用できるキーポイントからは大きな改善ポイントは検出されませんでした。"];
}

function localizedFaultFeedback(fault) {
  const messages = {
    door_swing_casting:
      "手が身体から早く離れている可能性があり、スイング軌道が大きくなってコンタクトが遅れやすくなります。",
    forward_axis_drift_rushing:
      "頭や上半身が早く前に動いている可能性があり、コンタクトのタイミングが不安定になりやすくなります。",
    arms_only_one_piece:
      "腰と肩が一緒に回っている可能性があり、下半身の力をスイングに使いにくくなります。",
    excessive_upper_swing_early_extension:
      "コンタクトに向けてスイング軌道が上向きになりすぎている可能性があります。",
    collapsed_lead_side:
      "インパクトで前側が柔らかくなっている可能性があり、力が前に逃げやすくなります。",
  };
  const severityText = fault.severity === "severe" ? "強く" : "可能性として";
  const evidence = fault.evidence ? ` 根拠: ${fault.evidence}` : "";
  return `${messages[fault.fault_type] ?? localizedValue(fault.fault_type)} ${severityText}示されています。${evidence}`;
}

function localizedDrills(feedback) {
  if (currentLanguage === "en") return feedback.drills_or_suggestions;
  const drillLabels = localizedGroup("drills");
  return (feedback.drills_or_suggestions ?? []).map((drill) => drillLabels[drill] ?? drill);
}

function localizedLimitations(limitations) {
  if (currentLanguage === "en") return limitations;
  return limitations.map((limitation) => localizedLimitation(limitation));
}

function localizedLimitation(limitation) {
  const knownLimitations = {
    "This is a 2D side-view rule-based evaluation and may miss 3D movement details.":
      "これは2D側面映像に基づくルール評価であり、3Dの動きの詳細を見落とす場合があります。",
    "Swing handedness was unknown, so lead/rear side mapping is lower confidence.":
      "打席が不明なため、リード側/後ろ側の対応づけの信頼度が下がっています。",
    "Automatic phase fallback used fewer than five unique frames.":
      "自動フェーズ推定で5つ未満の固有フレームしか使えませんでした。",
    "No sampled video frames were available for pose estimation.":
      "姿勢推定に使えるサンプル動画フレームがありませんでした。",
    "Pose detection covered fewer than 80% of sampled frames.":
      "姿勢検出はサンプルフレームの80%未満にとどまりました。",
    "Required body landmark coverage was low for swing evaluation.":
      "スイング評価に必要な身体ランドマークの網羅率が低くなっています。",
    "MediaPipe Pose tracks player body landmarks only; bat tip, bat barrel, and ball position are not detected.":
      "MediaPipe Pose は選手の身体ランドマークのみを追跡し、バット先端、バレル、ボール位置は検出しません。",
  };
  if (knownLimitations[limitation]) return knownLimitations[limitation];
  if (limitation.toLowerCase().includes("bat tip")) {
    return "バット先端、バレル、またはボール位置が検出されていないため、バット軌道に関する評価の信頼度は限定的です。";
  }
  if (limitation.toLowerCase().includes("mediapipe")) {
    return `MediaPipe 関連の制限: ${limitation}`;
  }
  return limitation;
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
    if (event.is_visible === false) continue;
    const item = document.createElement("li");
    const confidence =
      event.status === "skipped" || event.status === "unavailable"
        ? localizedValue(event.status)
        : formatNumber(event.confidence, 2);
    const eventText = t("result.event_row", {
      label: localizedValue(event.phase) || event.label,
      frameIndex: event.frame_index,
      confidence,
      method: formatLabel(event.detection_method),
    });
    const statusText = `${t("result.event_status")}: ${localizedValue(event.status)}`;
    item.textContent = event.fallback_reason
      ? `${eventText}, ${statusText}, ${t("result.event_fallback")}: ${event.fallback_reason}`
      : `${eventText}, ${statusText}`;
    swingEvents.append(item);
  }
}

function renderPoseQuality(
  poseDiagnostics,
  samplingDiagnostics,
  rawPoseDiagnostics = null,
  poseDebugDiagnostics = null,
  frameQualityDiagnostics = null,
  activeWindowDiagnostics = null,
  scoringEvidenceDiagnostics = null,
) {
  swingPoseQuality.replaceChildren();
  if (
    !poseDiagnostics &&
    !samplingDiagnostics &&
    !rawPoseDiagnostics &&
    !poseDebugDiagnostics &&
    !frameQualityDiagnostics &&
    !activeWindowDiagnostics &&
    !scoringEvidenceDiagnostics
  ) {
    appendDiagnostic(localizedDiagnosticLabel("sampling"), "-");
    appendDiagnostic(localizedDiagnosticLabel("pose_detection"), "-");
    appendDiagnostic(localizedDiagnosticLabel("landmark_coverage"), "-");
    appendDiagnostic(localizedDiagnosticLabel("phase_quality"), "-");
    return;
  }

  if (samplingDiagnostics) {
    appendDiagnostic(localizedDiagnosticLabel("quality_mode"), formatLabel(samplingDiagnostics.quality_mode));
    appendDiagnostic(localizedDiagnosticLabel("sampled_frames"), `${samplingDiagnostics.sampled_frame_count} / ${samplingDiagnostics.total_frame_count ?? "-"}`);
    appendDiagnostic(localizedDiagnosticLabel("effective_fps"), formatNumber(samplingDiagnostics.effective_fps, 2));
    appendDiagnostic(localizedDiagnosticLabel("cap_applied"), samplingDiagnostics.cap_applied ? (currentLanguage === "ja" ? "はい" : "Yes") : (currentLanguage === "ja" ? "いいえ" : "No"));
  }
  if (poseDiagnostics) {
    appendDiagnostic(localizedDiagnosticLabel("pose_detection"), `${formatNumber(poseDiagnostics.detected_pose_frame_ratio * 100, 0)}%`);
    appendDiagnostic(localizedDiagnosticLabel("landmark_coverage"), `${formatNumber(poseDiagnostics.required_landmark_coverage * 100, 0)}%`);
    appendDiagnostic(localizedDiagnosticLabel("mean_confidence"), formatNumber(poseDiagnostics.mean_confidence, 2));
    appendDiagnostic(localizedDiagnosticLabel("min_confidence"), formatNumber(poseDiagnostics.min_confidence, 2));
    appendDiagnostic(localizedDiagnosticLabel("smoothed_frames"), String(poseDiagnostics.smoothed_frame_count));
    appendDiagnostic(localizedDiagnosticLabel("interpolated_frames"), String(poseDiagnostics.interpolated_frame_count));
    appendDiagnostic(localizedDiagnosticLabel("rejected_outliers"), String(poseDiagnostics.rejected_outlier_count));
  }
  if (rawPoseDiagnostics) {
    appendDiagnostic(localizedDiagnosticLabel("raw_pose_detection"), `${formatNumber(rawPoseDiagnostics.detected_pose_frame_ratio * 100, 0)}%`);
    appendDiagnostic(localizedDiagnosticLabel("raw_landmark_coverage"), `${formatNumber(rawPoseDiagnostics.required_landmark_coverage * 100, 0)}%`);
  }
  if (poseDebugDiagnostics) {
    appendDiagnostic(localizedDiagnosticLabel("pose_mode"), formatLabel(poseDebugDiagnostics.processing_mode));
    appendDiagnostic(localizedDiagnosticLabel("mediapipe_running_mode"), formatLabel(poseDebugDiagnostics.running_mode));
    appendDiagnostic(localizedDiagnosticLabel("requested_poses"), String(poseDebugDiagnostics.requested_num_poses));
    appendDiagnostic(localizedDiagnosticLabel("selection_strategy"), formatLabel(poseDebugDiagnostics.player_selection_strategy));
    appendDiagnostic(localizedDiagnosticLabel("selected_candidates"), (poseDebugDiagnostics.selected_candidate_indexes ?? []).join(", ") || "-");
    appendDiagnostic(localizedDiagnosticLabel("candidate_switches"), String(poseDebugDiagnostics.candidate_switch_count ?? 0));
    appendDiagnostic(localizedDiagnosticLabel("candidate_ambiguity"), String(poseDebugDiagnostics.candidate_ambiguity_count ?? 0));
    appendDiagnostic(localizedDiagnosticLabel("max_stabilization_delta"), formatNumber(poseDebugDiagnostics.max_stabilization_delta_ratio, 2));
    appendDiagnostic(localizedDiagnosticLabel("changed_keypoints"), String(poseDebugDiagnostics.stabilization_changed_keypoint_count ?? 0));
  }
  if (frameQualityDiagnostics) {
    appendDiagnostic(
      localizedDiagnosticLabel("frame_quality"),
      `${frameQualityDiagnostics.usable_frame_count} / ${frameQualityDiagnostics.total_frame_count}`,
    );
    appendDiagnostic(localizedDiagnosticLabel("weak_frames"), String(frameQualityDiagnostics.weak_frame_count ?? 0));
    appendDiagnostic(localizedDiagnosticLabel("rejected_frames"), String(frameQualityDiagnostics.rejected_frame_count ?? 0));
  }
  if (activeWindowDiagnostics) {
    appendDiagnostic(
      localizedDiagnosticLabel("active_window"),
      `${activeWindowDiagnostics.start_frame_index}-${activeWindowDiagnostics.end_frame_index} (${formatNumber(activeWindowDiagnostics.confidence, 2)})`,
    );
    appendDiagnostic(localizedDiagnosticLabel("active_window_peak"), String(activeWindowDiagnostics.peak_motion_frame_index));
  }
  if (scoringEvidenceDiagnostics) {
    appendDiagnostic(
      localizedDiagnosticLabel("scoring_evidence"),
      String(scoringEvidenceDiagnostics.affected_metrics?.length ?? 0),
    );
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
    appendCell(row, formatLabel(metric.name), "metrics-name-column");
    appendCell(row, metric.value === null ? "-" : formatNumber(metric.value, 2));
    appendCell(row, formatLabel(metric.unit ?? ""));
    appendCell(row, formatTarget(metric.target_min, metric.target_max));
    appendCell(row, formatLabel(metric.severity));
    appendCell(row, formatNumber(metric.deduction, 2));
    appendScrollableCell(
      row,
      (metric.evidence_frames ?? []).join(", "),
      "metrics-evidence-column",
      "metrics-evidence",
    );
    swingMetrics.append(row);
  }
}

function renderFaults(faults) {
  swingFaults.replaceChildren();
  if (!faults?.length) {
    const empty = document.createElement("p");
    empty.textContent = t("result.no_faults");
    swingFaults.append(empty);
    return;
  }

  const list = document.createElement("ul");
  for (const fault of faults) {
    const item = document.createElement("li");
    item.className = "fault-item";
    item.append(
      t("result.fault_row", {
        faultType: formatLabel(fault.fault_type),
        phase: formatLabel(fault.phase),
        severity: formatLabel(fault.severity),
      }),
    );
    const evidence = document.createElement("div");
    evidence.className = "evidence-cell fault-evidence";
    evidence.tabIndex = 0;
    evidence.textContent = t("result.fault_evidence", {
      evidence: fault.evidence,
      frames: (fault.evidence_frames ?? []).join(", "),
    });
    item.append(evidence);
    list.append(item);
  }
  swingFaults.append(list);
}

function appendCell(row, value, className = "") {
  const cell = document.createElement("td");
  if (className) cell.className = className;
  const content = document.createElement("div");
  content.className = "table-cell-content";
  content.textContent = value;
  if (String(value).length > 32) content.tabIndex = 0;
  cell.append(content);
  row.append(cell);
}

function appendScrollableCell(row, value, columnClassName, contentClassName) {
  const cell = document.createElement("td");
  cell.className = columnClassName;
  const content = document.createElement("div");
  content.className = `table-cell-content evidence-cell ${contentClassName}`;
  content.tabIndex = 0;
  content.textContent = value || "-";
  cell.append(content);
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
  const hasActiveOverlay = poseOverlayEnabled || evaluationLinesEnabled;
  if (poseOverlayEnabled) {
    drawSkeletonLines(context, keypoints, contentRect);
  }
  if (evaluationLinesEnabled) {
    drawEvaluationOverlayLines(context, frame, contentRect);
  }
  if (poseOverlayEnabled) {
    for (const keypoint of frame.keypoints) {
      drawKeypoint(context, keypoint, contentRect, frame.is_event_frame);
    }
  }
  if (hasActiveOverlay && frame.is_event_frame) {
    drawEventLabel(context, frame, canvas.width);
  }
  poseOverlayStatus.textContent = t("overlay.showing", {
    message: overlayMessage(),
    matchStatus: overlayFrameMatchStatus(frame),
    source: formatLabel(frame.source ?? poseOverlaySource.value),
    frameIndex: frame.frame_index,
  });
}

function updatePoseOverlayToggle() {
  const hasPoseFrames = analysisOverlayFrames.length > 0 || analysisRawOverlayFrames.length > 0;
  poseOverlayToggle.disabled = !hasPoseFrames;
  poseOverlayToggle.setAttribute("aria-pressed", poseOverlayEnabled ? "true" : "false");
  poseOverlayToggle.classList.toggle("is-active", poseOverlayEnabled);
}

function updateEvaluationLinesToggle() {
  const hasLines = analysisEvaluationOverlay.length > 0;
  evaluationLinesToggle.disabled = !hasLines;
  evaluationLinesToggle.setAttribute("aria-pressed", evaluationLinesEnabled ? "true" : "false");
  evaluationLinesToggle.classList.toggle("is-active", evaluationLinesEnabled);
}

function updateEvaluationMetricSelect({ preserveSelection = true } = {}) {
  const metricNames = evaluationMetricNames();
  const previousSelection = preserveSelection ? new Set(selectedEvaluationMetrics) : new Set();
  evaluationMetricMenu.replaceChildren();
  evaluationMetricMenu.append(
    evaluationMetricMenuItem({
      value: allEvaluationMetricsValue,
      label: t("overlay.all_metrics"),
      checked: selectedEvaluationMetrics.size === 0,
    }),
  );

  for (const metricName of metricNames) {
    evaluationMetricMenu.append(
      evaluationMetricMenuItem({
        value: metricName,
        label: formatEvaluationMetricLabel(metricName),
        checked: previousSelection.has(metricName),
      }),
    );
  }

  selectedEvaluationMetrics.clear();
  for (const metricName of metricNames) {
    if (previousSelection.has(metricName)) {
      selectedEvaluationMetrics.add(metricName);
    }
  }
  syncEvaluationMetricSelectSelection();
  evaluationMetricToggle.disabled = metricNames.length === 0;
  if (metricNames.length === 0) closeEvaluationMetricMenu();
}

function evaluationMetricMenuItem({ value, label, checked }) {
  const item = document.createElement("label");
  item.className = "metric-dropdown-item";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.value = value;
  checkbox.checked = checked;
  item.append(checkbox, label);
  return item;
}

function syncEvaluationMetricSelectSelection() {
  for (const checkbox of evaluationMetricMenu.querySelectorAll("input[type='checkbox']")) {
    checkbox.checked =
      selectedEvaluationMetrics.size === 0
        ? checkbox.value === allEvaluationMetricsValue
        : selectedEvaluationMetrics.has(checkbox.value);
  }
  evaluationMetricToggle.textContent = selectedEvaluationMetricLabel();
}

function selectedEvaluationMetricLabel() {
  if (selectedEvaluationMetrics.size === 0) return t("overlay.all_metrics");
  if (selectedEvaluationMetrics.size === 1) {
    const [metricName] = selectedEvaluationMetrics;
    return formatEvaluationMetricLabel(metricName);
  }
  return t("overlay.metric_groups_mode", { count: selectedEvaluationMetrics.size });
}

function evaluationMetricNames() {
  const metricNames = [];
  const seenMetricNames = new Set();
  for (const line of analysisEvaluationOverlay) {
    if (!line.metric_name || seenMetricNames.has(line.metric_name)) continue;
    seenMetricNames.add(line.metric_name);
    metricNames.push(line.metric_name);
  }
  return metricNames;
}

poseOverlayToggle.addEventListener("click", () => {
  if (!currentOverlayFrames().length) return;
  poseOverlayEnabled = !poseOverlayEnabled;
  updatePoseOverlayToggle();
  drawPoseOverlay();
});

evaluationLinesToggle.addEventListener("click", () => {
  if (!analysisEvaluationOverlay.length) return;
  evaluationLinesEnabled = !evaluationLinesEnabled;
  updateEvaluationLinesToggle();
  drawPoseOverlay();
});

evaluationMetricToggle.addEventListener("click", () => {
  if (evaluationMetricToggle.disabled) return;
  const shouldOpen = evaluationMetricMenu.hidden;
  evaluationMetricMenu.hidden = !shouldOpen;
  evaluationMetricToggle.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
});

evaluationMetricMenu.addEventListener("change", (event) => {
  if (event.target instanceof HTMLInputElement) {
    syncSelectedEvaluationMetricsFromMenu(event.target);
    drawPoseOverlay();
  }
});

document.addEventListener("click", (event) => {
  const clickTarget = event.target;
  if (
    !evaluationMetricMenu.hidden &&
    (!(clickTarget instanceof Element) || !clickTarget.closest(".metric-control"))
  ) {
    closeEvaluationMetricMenu();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeEvaluationMetricMenu();
  }
});

function syncSelectedEvaluationMetricsFromMenu(changedCheckbox) {
  if (changedCheckbox.value === allEvaluationMetricsValue) {
    selectedEvaluationMetrics.clear();
  } else if (changedCheckbox.checked) {
    selectedEvaluationMetrics.add(changedCheckbox.value);
  } else {
    selectedEvaluationMetrics.delete(changedCheckbox.value);
  }
  syncEvaluationMetricSelectSelection();
}

function closeEvaluationMetricMenu() {
  evaluationMetricMenu.hidden = true;
  evaluationMetricToggle.setAttribute("aria-expanded", "false");
}

function overlayFrameMatchStatus(frame) {
  const hasInterpolatedLandmarks = frame.keypoints.some((keypoint) => keypoint.interpolated);
  const fpsValue = activeManifest?.fps;
  const frameTime = Number.isFinite(frame.timestamp_seconds) ? frame.timestamp_seconds : null;
  const offsetMs = frameTime === null ? null : Math.round((frameTime - videoPlayer.currentTime) * 1000);
  const offsetText = offsetMs === null || offsetMs === 0 ? "" : t("overlay.offset", { offsetMs });
  if (hasInterpolatedLandmarks) return t("overlay.interpolated", { offset: offsetText });
  if (!fpsValue) return t("overlay.nearest_sampled", { offset: offsetText });
  const currentFrameIndex = Math.round(videoPlayer.currentTime * fpsValue);
  return currentFrameIndex === frame.frame_index
    ? t("overlay.exact_sampled")
    : t("overlay.nearest_sampled", { offset: offsetText });
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
  context.restore();
}

function drawEvaluationOverlayLines(context, frame, contentRect) {
  const lines = evaluationLinesForFrame(frame);
  if (!lines.length) return;

  context.save();
  for (const line of lines) {
    const start = overlayPoint(line.start, contentRect);
    const end = overlayPoint(line.end, contentRect);
    context.strokeStyle = evaluationLineColor(line);
    context.lineWidth = line.style === "reference" ? 2 : 3;
    context.setLineDash(line.style === "dashed" || line.style === "reference" ? [8, 6] : []);
    context.beginPath();
    context.moveTo(start.x, start.y);
    context.lineTo(end.x, end.y);
    context.stroke();
    drawEvaluationLineLabel(context, line, start, end);
  }
  context.restore();
}

function evaluationLinesForFrame(frame) {
  const currentFrameIndex = frame.frame_index;
  const eventWindow = analysisEvents.find(
    (event) =>
      currentFrameIndex >= event.start_frame_index && currentFrameIndex <= event.end_frame_index,
  );
  const eventFrameIndex = eventWindow?.frame_index ?? currentFrameIndex;
  return selectedEvaluationLines().filter(
    (line) => line.frame_index === currentFrameIndex || line.frame_index === eventFrameIndex,
  );
}

function selectedEvaluationLines() {
  if (selectedEvaluationMetrics.size === 0) return analysisEvaluationOverlay;
  return analysisEvaluationOverlay.filter(
    (line) => selectedEvaluationMetrics.has(line.metric_name),
  );
}

function evaluationLineColor(line) {
  const colors = {
    good: "rgba(30, 150, 92, 0.9)",
    warning: "rgba(217, 119, 6, 0.92)",
    severe: "rgba(220, 38, 38, 0.92)",
    neutral: "rgba(37, 99, 235, 0.88)",
    low_confidence: "rgba(148, 163, 184, 0.86)",
  };
  return colors[line.color_role] ?? colors.neutral;
}

function drawEvaluationLineLabel(context, line, start, end) {
  const label = formatEvaluationMetricLabel(line.metric_name) || line.label;
  const x = (start.x + end.x) / 2;
  const y = (start.y + end.y) / 2;
  context.font = "700 11px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  context.textBaseline = "middle";
  const textWidth = context.measureText(label).width;
  const labelX = clamp(x + 6, 2, poseOverlayCanvas.width - textWidth - 8);
  const labelY = clamp(y - 8, 14, poseOverlayCanvas.height - 14);
  context.fillStyle = "rgba(15, 23, 32, 0.72)";
  context.fillRect(labelX - 3, labelY - 9, textWidth + 6, 18);
  context.fillStyle = "#ffffff";
  context.fillText(label, labelX, labelY);
}

function drawEventLabel(context, frame, width) {
  const event = analysisEvents.find((item) => item.frame_index === frame.frame_index);
  if (!event) return;
  context.save();
  context.font = "700 13px -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
  const label = localizedValue(event.phase) || event.label;
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
  if (!activeManifest) return t("overlay.hidden_select");
  if (!currentOverlayFrames().length) return t("overlay.hidden_run");
  const activeModes = [];
  if (poseOverlayEnabled) activeModes.push(t("overlay.poses_mode"));
  if (evaluationLinesEnabled) {
    activeModes.push(evaluationLinesMessage());
  }
  if (!activeModes.length) return t("overlay.hidden_off");
  return t("overlay.active", { modes: activeModes.join(" + ") });
}

function evaluationLinesMessage() {
  if (selectedEvaluationMetrics.size === 0) return t("overlay.evaluation_lines_mode");
  if (selectedEvaluationMetrics.size === 1) {
    const [metricName] = selectedEvaluationMetrics;
    return t("overlay.metric_lines_mode", { metricLabel: formatEvaluationMetricLabel(metricName) });
  }
  return t("overlay.metric_groups_mode", { count: selectedEvaluationMetrics.size });
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
  playbackError.textContent = t("status.video_error");
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
applyLanguage();
clearAnalysis({ status: t("status.select_analysis_video") });
updateSwingRunState();
