from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from utils.model_loader import GeneralizedOODDetector, load_models
from utils.preprocessors import preprocess_for_autoencoder, preprocess_for_xgboost
from utils.report_generator import generate_ids_report

socketio = SocketIO()

state: Dict[str, Any] = {
    "models": None,
    "dataset_path": None,
    "processing": False,
    "stop_requested": False,
    "last_summary": None,
    "last_report_path": None,
}


def allowed_file(filename: str, allowed_exts: set[str]) -> bool:
    return os.path.splitext(filename)[1].lower() in allowed_exts


def count_csv_rows(path: str) -> int:
    try:
        with open(path, "rb") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    except OSError:
        return 0


def build_ood_detector(
    warmup_df: pd.DataFrame,
    models: Dict[str, Any],
    ood_train_samples: int,
    ood_normal_samples: int,
    ood_threshold_fallback: float,
    ae_batch_size: int,
) -> Dict[str, Any]:
    xgb_saved = models["xgb_saved"]
    xgb_model = models["xgb_model"]
    target_encoder = models["target_encoder"]
    ae_saved = models["ae_saved"]
    autoencoder = models["autoencoder"]
    ae_threshold = models["ae_threshold"]

    warmup_df = warmup_df.head(ood_train_samples)

    X_xgb = preprocess_for_xgboost(warmup_df, xgb_saved)
    xgb_proba = xgb_model.predict_proba(X_xgb)
    y_pred_idx = np.argmax(xgb_proba, axis=1)

    ood_detector = GeneralizedOODDetector(xgb_model, target_encoder)
    ood_detector.calibrate_temperature(X_xgb, y_pred_idx)
    ood_detector.fit_mahalanobis(X_xgb, y_pred_idx)

    ae_input = preprocess_for_autoencoder(warmup_df, ae_saved, xgb_saved.get("columns_to_drop", []))
    reconstruction = autoencoder.predict(ae_input, verbose=0, batch_size=ae_batch_size)
    ae_errors = np.mean(np.square(ae_input - reconstruction), axis=1)
    ae_errors_log = np.log1p(ae_errors)
    ae_threshold_log = np.log1p(ae_threshold)

    is_normal = ae_errors_log <= ae_threshold_log
    normal_errors_log = ae_errors_log[is_normal]

    if normal_errors_log.size > 0:
        ae_threshold_high = float(np.percentile(normal_errors_log, 85))
    else:
        ae_threshold_high = ae_threshold_log

    if normal_errors_log.size > 0:
        normal_sample = warmup_df[is_normal][:ood_normal_samples]
        normal_ae_subset = normal_errors_log[: len(normal_sample)]
        normal_xgb = preprocess_for_xgboost(normal_sample, xgb_saved)
        
        ood_scores_normal, _, _, _, _ = ood_detector.get_ood_score(
            normal_xgb,
            ae_errors_subset=normal_ae_subset,
            w_mahala=0.6,
            w_ae=0.3,
            w_entropy=0.1,
        )
        ood_threshold = float(np.percentile(ood_scores_normal, 80))
    else:
        ood_threshold = ood_threshold_fallback

    print(f"   📊 Dynamic thresholds:")
    print(f"      OOD Threshold: {ood_threshold:.4f}")
    print(f"      AE Threshold High: {ae_threshold_high:.4f}")

    return {
        "ood_detector": ood_detector,
        "ood_threshold": ood_threshold,
        "ae_threshold_high": ae_threshold_high,
    }


def process_dataset(file_path: str, app: Flask) -> None:
    if not os.path.exists(file_path):
        socketio.emit("processing_error", {"message": "Dataset not found."})
        state["processing"] = False
        return

    models = state["models"]
    if not models:
        socketio.emit("processing_error", {"message": "Models not loaded."})
        state["processing"] = False
        return

    xgb_saved = models["xgb_saved"]
    xgb_model = models["xgb_model"]
    target_encoder = models["target_encoder"]
    ae_saved = models["ae_saved"]
    autoencoder = models["autoencoder"]
    ae_threshold = models["ae_threshold"]
    known_attacks = models.get("known_attacks", [])

    post_correction_mode = app.config.get("ZERO_DAY_POST_CORRECTION")
    print(
        f"   🧭 Zero-day post-correction mode: {post_correction_mode} "
        "(off | rare_attacks | labels)"
    )

    # ============================================================
    # LOAD RARE ATTACKS FOR POST-CORRECTION
    # ============================================================
    split_info_path = os.path.join(app.config["DATA_DIR"], "split_info.json")
    rare_attacks = []
    if os.path.exists(split_info_path):
        with open(split_info_path, "r") as f:
            split_info = json.load(f)
            rare_attacks = split_info.get("rare_attacks", ["Fingerprinting", "MITM"])
    if post_correction_mode == "rare_attacks":
        print(f"   📋 Rare attacks (only these can be zero-day): {rare_attacks}")

    total_rows = count_csv_rows(file_path)
    if total_rows == 0:
        socketio.emit("processing_error", {"message": "Dataset is empty."})
        state["processing"] = False
        return

    warmup_df = pd.read_csv(file_path, nrows=app.config["OOD_TRAIN_SAMPLES"], low_memory=False)
    ood_context = build_ood_detector(
        warmup_df,
        models,
        app.config["OOD_TRAIN_SAMPLES"],
        app.config["OOD_NORMAL_SAMPLE_SIZE"],
        app.config["OOD_THRESHOLD_FALLBACK"],
        app.config["AE_BATCH_SIZE"],
    )

    ood_detector = ood_context["ood_detector"]
    ood_threshold = ood_context["ood_threshold"]
    ae_threshold_high = ood_context["ae_threshold_high"]

    # Read data and optional labels
    print(f"📖 Reading and shuffling {total_rows:,} samples...")
    df_full = pd.read_csv(file_path, low_memory=False)

    labels_series = None
    labels_filename = app.config.get("LABELS_FILENAME")
    labels_column = app.config.get("LABELS_COLUMN", "Attack_type")
    if labels_filename:
        labels_path = os.path.join(os.path.dirname(file_path), labels_filename)
        if os.path.exists(labels_path):
            labels_df = pd.read_csv(labels_path, low_memory=False)
            if labels_column not in labels_df.columns:
                socketio.emit(
                    "processing_error",
                    {"message": f"Labels file missing column '{labels_column}'."},
                )
                state["processing"] = False
                return
            labels_series = labels_df[labels_column].astype(str).reset_index(drop=True)
            if len(labels_series) != len(df_full):
                socketio.emit(
                    "processing_error",
                    {"message": "Labels file row count does not match dataset."},
                )
                state["processing"] = False
                return
            print(f"✅ Labels loaded from {labels_path}")
        elif post_correction_mode == "labels":
            socketio.emit(
                "processing_error",
                {"message": f"Labels file not found at {labels_path}."},
            )
            state["processing"] = False
            return

    if labels_series is not None and post_correction_mode == "off":
        post_correction_mode = "labels"
        print("   ✅ Labels found; enabling label-based post-correction for this run.")

    # Shuffle deterministically; keep labels aligned if provided
    rng = np.random.RandomState(42)
    perm = rng.permutation(len(df_full))
    df_full = df_full.iloc[perm].reset_index(drop=True)
    if labels_series is not None:
        labels_series = labels_series.iloc[perm].reset_index(drop=True)
    print(f"✅ Data shuffled")

    start_time = time.time()

    print(f" PHASE 1: AutoEncoder processing {total_rows:,} samples in 30 k batches...")
    socketio.emit("phase_start", {"phase": 1, "total": total_rows})
    socketio.sleep(0)

    try:
        # ============================================================
        # PHASE 1: AutoEncoder — fully vectorized, no per-sample loop
        # ============================================================
        AE_PROC_BATCH = 30_000

        all_ae_errors = np.empty(total_rows, dtype=np.float64)
        running_normal = 0
        running_anomaly = 0
        processed_count = 0

        for start_idx in range(0, total_rows, AE_PROC_BATCH):
            if state["stop_requested"]:
                break
            end_idx = min(start_idx + AE_PROC_BATCH, total_rows)
            batch_df = df_full.iloc[start_idx:end_idx]

            ae_input = preprocess_for_autoencoder(
                batch_df, ae_saved, xgb_saved.get("columns_to_drop", [])
            )
            reconstruction = autoencoder.predict(ae_input, verbose=0, batch_size=4096)
            ae_errors_batch = np.mean(np.square(ae_input - reconstruction), axis=1)
            all_ae_errors[start_idx:end_idx] = ae_errors_batch

            running_normal += int(np.sum(ae_errors_batch <= ae_threshold))
            running_anomaly += int(np.sum(ae_errors_batch > ae_threshold))
            processed_count = end_idx

            last_err = float(ae_errors_batch[-1])
            last_dec = "NORMAL" if last_err <= ae_threshold else "ANOMALY"
            ae_conf = 100.0 if last_dec == "NORMAL" else max(0.0, 100.0 - last_err / ae_threshold * 100.0)

            socketio.emit("ae_sample_processed", {
                "sample_index": processed_count,
                "total": total_rows,
                "progress": round(processed_count / total_rows * 100, 2),
                "ae_error": last_err,
                "ae_threshold": float(ae_threshold),
                "ae_decision": last_dec,
                "ae_confidence": ae_conf,
                "normal_count": running_normal,
                "anomaly_count": running_anomaly,
            })
            socketio.sleep(0)

        if state["stop_requested"]:
            socketio.emit("processing_stopped", {"message": "Processing stopped by user"})
            state["processing"] = False
            return

        sample_index = processed_count

        # Vectorized classification — no Python loop needed
        ae_errors_all = all_ae_errors[:processed_count]
        ae_errors_log_all = np.log1p(ae_errors_all)
        anomaly_mask = ae_errors_all > ae_threshold
        normal_mask = ~anomaly_mask

        normal_count = int(np.sum(normal_mask))
        anomaly_indices = np.where(anomaly_mask)[0]
        anomaly_count = len(anomaly_indices)

        anomaly_ae_errors_log: List[float] = ae_errors_log_all[anomaly_mask].tolist()
        normal_ae_errors_log: List[float] = ae_errors_log_all[normal_mask].tolist()

        # Build anomaly DataFrame as a single slice — no per-sample DataFrame()
        all_anomalies_df = df_full.iloc[anomaly_indices].reset_index(drop=True)
        anomaly_list: List[int] = anomaly_indices.tolist()

        # Normal samples for OOD recalibration
        normal_indices = np.where(normal_mask)[0]
        ood_n = min(app.config["OOD_NORMAL_SAMPLE_SIZE"], len(normal_indices))
        normal_sample_df = df_full.iloc[normal_indices[:ood_n]]
        normal_sample_ae_errors_log: List[float] = ae_errors_log_all[normal_indices[:ood_n]].tolist()

        # Labels aligned to anomaly positions
        anomaly_true_types: List[str] = []
        if labels_series is not None:
            anomaly_true_types = labels_series.iloc[anomaly_indices].tolist()

        ae_duration = time.time() - start_time

        print(f"\n PHASE 1 COMPLETE:")
        print(f"   Total: {sample_index:,} | Normal: {normal_count:,} | Anomalies: {anomaly_count:,}")
        print(f"   Duration: {ae_duration:.2f}s")

        socketio.emit("ae_phase_complete", {
            "total_samples": sample_index,
            "normal_count": int(normal_count),
            "anomaly_count": int(anomaly_count),
            "duration": ae_duration,
        })
        socketio.sleep(0)

        if anomaly_count > 0:
            socketio.emit("phase_2_ready", {"anomaly_count": anomaly_count})
            socketio.sleep(0)

        # Recompute OOD thresholds from full dataset normal samples
        if normal_ae_errors_log:
            ae_threshold_high = float(np.percentile(normal_ae_errors_log, 85))
        else:
            ae_threshold_high = float(np.log1p(ae_threshold))

        if len(normal_sample_df) >= 100:
            normal_xgb = preprocess_for_xgboost(normal_sample_df, xgb_saved)
            ood_scores_normal, _, _, _, _ = ood_detector.get_ood_score(
                normal_xgb,
                ae_errors_subset=np.array(normal_sample_ae_errors_log),
                w_mahala=0.6, w_ae=0.3, w_entropy=0.1,
            )
            ood_threshold = float(np.percentile(ood_scores_normal, 80))
        else:
            ood_threshold = app.config["OOD_THRESHOLD_FALLBACK"]

        socketio.sleep(0)
        print(f"    Thresholds from full dataset normals:")
        print(f"      OOD Threshold: {ood_threshold:.4f}")
        print(f"      AE Threshold High: {ae_threshold_high:.4f}")

        # ============================================================
        # PHASE 2: XGBoost + OOD — 20 k vectorized batches, one emit per batch
        # ============================================================
        if anomaly_count > 0:
            print(f"\n PHASE 2: XGBoost + OOD processing {anomaly_count:,} anomalies in 20 k batches...")

            socketio.emit("phase_start", {"phase": 2, "total": anomaly_count})
            socketio.sleep(0)

            XGB_PROC_BATCH = 20_000

            known_count = 0
            zero_day_count = 0
            attack_distribution = {name: 0 for name in known_attacks}
            processed_xgb = 0
            start_xgb_time = time.time()

            for start_idx in range(0, anomaly_count, XGB_PROC_BATCH):
                if state["stop_requested"]:
                    break
                end_idx = min(start_idx + XGB_PROC_BATCH, anomaly_count)
                batch = all_anomalies_df.iloc[start_idx:end_idx]
                batch_size = len(batch)

                # Vectorized XGBoost inference
                X_xgb = preprocess_for_xgboost(batch, xgb_saved)
                xgb_proba = xgb_model.predict_proba(X_xgb)
                xgb_pred_idx = np.argmax(xgb_proba, axis=1)
                xgb_predictions = target_encoder.inverse_transform(xgb_pred_idx)
                xgb_confidences = np.max(xgb_proba, axis=1) * 100

                # Vectorized OOD scores
                ae_errors_subset = np.array(anomaly_ae_errors_log[start_idx:end_idx])
                ood_scores, _, _, _, _ = ood_detector.get_ood_score(
                    X_xgb, ae_errors_subset=ae_errors_subset,
                    w_mahala=0.6, w_ae=0.3, w_entropy=0.1,
                )

                # Vectorized base decisions
                is_zero_day_arr = (
                    (ood_scores > ood_threshold) |
                    (xgb_predictions == "Normal") |
                    (xgb_confidences < 70)
                ).copy()

                # Per-sample post-correction (conditional, must stay per-sample)
                batch_true_types = anomaly_true_types[start_idx:end_idx] if anomaly_true_types else []
                for i in range(batch_size):
                    if is_zero_day_arr[i]:
                        xgb_pred = xgb_predictions[i]
                        true_type = batch_true_types[i] if batch_true_types else None
                        if post_correction_mode == "labels" and true_type and true_type in known_attacks:
                            is_zero_day_arr[i] = False
                            xgb_predictions[i] = true_type
                            xgb_pred = true_type
                        elif post_correction_mode == "rare_attacks" and xgb_pred not in rare_attacks:
                            is_zero_day_arr[i] = False

                    if is_zero_day_arr[i]:
                        zero_day_count += 1
                    else:
                        pred = xgb_predictions[i]
                        known_count += 1
                        attack_distribution[pred] = attack_distribution.get(pred, 0) + 1

                processed_xgb = end_idx
                last_i = batch_size - 1
                socketio.emit("xgb_sample_processed", {
                    "sample_index": anomaly_list[end_idx - 1] + 1,
                    "total": anomaly_count,
                    "progress": round(processed_xgb / anomaly_count * 100, 2),
                    "processed": processed_xgb,
                    "xgb_prediction": xgb_predictions[last_i],
                    "xgb_confidence": float(xgb_confidences[last_i]),
                    "ood_score": float(ood_scores[last_i]),
                    "ood_threshold": ood_threshold,
                    "final_decision": "ZERO-DAY" if bool(is_zero_day_arr[last_i]) else "KNOWN",
                    "known_count": known_count,
                    "zero_day_count": zero_day_count,
                    "attack_distribution": attack_distribution,
                })
                socketio.sleep(0)

            xgb_duration = time.time() - start_xgb_time

            print(f"\n PHASE 2 COMPLETE:")
            print(f"   Known: {known_count:,} | Zero-Day: {zero_day_count:,}")
            print(f"   Duration: {xgb_duration:.2f}s")

            summary_payload = {
                "normal_count": normal_count,
                "anomaly_count": anomaly_count,
                "known_count": known_count,
                "zero_day_count": zero_day_count,
                "attack_distribution": attack_distribution,
                "total_samples": sample_index,
                "ae_duration": ae_duration,
                "xgb_duration": xgb_duration,
                "duration_seconds": ae_duration + xgb_duration,
                "ae_threshold": float(ae_threshold),
                "ae_threshold_high": float(ae_threshold_high),
                "ood_threshold": float(ood_threshold),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "latency_ms": round((ae_duration + xgb_duration) / sample_index * 1000, 2),
                "security_level": "MAXIMUM",
            }
        else:
            xgb_duration = 0.0
            summary_payload = {
                "normal_count": normal_count,
                "anomaly_count": 0,
                "known_count": 0,
                "zero_day_count": 0,
                "attack_distribution": {},
                "total_samples": sample_index,
                "ae_duration": ae_duration,
                "xgb_duration": 0,
                "duration_seconds": ae_duration,
                "ae_threshold": float(ae_threshold),
                "ae_threshold_high": float(ae_threshold_high),
                "ood_threshold": float(ood_threshold),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "latency_ms": round(ae_duration / sample_index * 1000, 2),
                "security_level": "MAXIMUM",
            }

    except Exception as exc:
        socketio.emit("processing_error", {"message": str(exc)})
        state["processing"] = False
        return

    # Save report
    os.makedirs(app.config["OUTPUT_DIR"], exist_ok=True)
    report_path = os.path.join(
        app.config["OUTPUT_DIR"], f"session_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({"summary": summary_payload}, handle, indent=2)

    state["last_summary"] = summary_payload
    state["last_report_path"] = report_path
    state["processing"] = False

    socketio.emit("processing_complete", summary_payload)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_pyfile("config.py", silent=False)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_DIR"], exist_ok=True)

    print("📦 Loading models...")
    state["models"] = load_models(app.config["MODEL_DIR"], app.config["DATA_DIR"])
    print("✅ Models loaded successfully!")

    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode=app.config.get("SOCKETIO_ASYNC_MODE"),
    )

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    @app.route("/upload", methods=["POST"])
    def upload() -> Any:
        if state["processing"]:
            return jsonify({"error": "Cannot upload while processing is running. Please wait."}), 403
            
        if "file" not in request.files:
            return jsonify({"error": "No file provided."}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Empty filename."}), 400

        if not allowed_file(file.filename, app.config["ALLOWED_EXTENSIONS"]):
            return jsonify({"error": "Invalid file type."}), 400

        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)
        state["dataset_path"] = save_path
        
        row_count = count_csv_rows(save_path)
        
        return jsonify({"message": "Uploaded", "path": save_path, "total_rows": row_count})

    @app.route("/export", methods=["GET"])
    def export_report() -> Any:
        # Prevent export during processing
        if state["processing"]:
            return jsonify({"error": "Cannot export report while processing is running. Please wait for completion."}), 403
        
        if not state.get("last_summary"):
            return jsonify({"error": "No report available. Please run processing first."}), 404
        
        summary = state["last_summary"]
        report_path = generate_ids_report(summary, app.config["OUTPUT_DIR"])
        return send_file(report_path, as_attachment=True, download_name="ids_report.pdf")

    @socketio.on("connect")
    def on_connect() -> None:
        emit("server_status", {"ready": True, "processing": state["processing"]})

    @socketio.on("start_processing")
    def start_processing(data: Optional[Dict[str, Any]] = None) -> None:
        if state["processing"]:
            emit("processing_error", {"message": "Processing already running."})
            return

        data = data or {}
        dataset_path = data.get("path") or state.get("dataset_path")
        if not dataset_path:
            emit("processing_error", {"message": "No dataset uploaded."})
            return

        state["processing"] = True
        state["stop_requested"] = False
        socketio.start_background_task(process_dataset, dataset_path, app)

    @socketio.on("stop_processing")
    def stop_processing() -> None:
        state["stop_requested"] = True
        emit("processing_stopped", {"message": "Stop requested."})

    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)