# InduSentry — IDS-IIoT Security Platform

An AI-based Hybrid Intrusion Detection System for Industrial IoT networks, built with Flask and Socket.IO. Features a real-time dashboard that streams detection results as they happen and generates professional PDF reports.

---

## How It Works

The system processes network traffic through a three-stage hybrid pipeline:

1. **AutoEncoder (Unsupervised)** — Trained exclusively on normal IIoT traffic from the Edge-IIoTset dataset. Flags any sample whose reconstruction error exceeds the learned threshold as anomalous.
2. **XGBoost Classifier (Supervised)** — Receives only the anomalous samples and predicts the attack category (multi-class).
3. **OOD Detector** — Scores each classified sample using a weighted combination of Mahalanobis distance (60%), AE reconstruction error (30%), and prediction entropy (10%) to distinguish known attacks from zero-day threats.

## Stack

- **Backend** — Python, Flask, Flask-SocketIO (eventlet)
- **ML** — TensorFlow/Keras (AutoEncoder), XGBoost, scikit-learn
- **Frontend** — Tailwind CSS (dark theme), Vanilla JS, Socket.IO client
- **Reports** — ReportLab, Matplotlib

## Project Structure

```
├── app.py                  # Flask app + Socket.IO processing pipeline
├── config.py               # Configuration (batch sizes, paths, thresholds)
├── run.py                  # Entry point
├── models/                 # Trained AutoEncoder and XGBoost models
├── data/                   # Threshold config and known attack list
├── utils/
│   ├── model_loader.py     # Model loading and OOD detector
│   ├── preprocessors.py    # Feature engineering for AE and XGBoost
│   └── report_generator.py # PDF report generation
├── templates/index.html    # Dashboard UI
├── static/                 # CSS, JS, SVG assets
└── X_test_hybrid.csv       # Test dataset (Edge-IIoTset hybrid)
```

## Setup

```bash
pip install -r requirements.txt
python run.py
```

Open `http://localhost:5000`, upload the CSV test file, and click **Start Processing**.

## Dataset

Built and evaluated on the **Edge-IIoTset** dataset — a realistic IIoT network traffic dataset covering normal traffic and multiple attack categories including DoS, DDoS, MITM, injection, and scanning attacks.
