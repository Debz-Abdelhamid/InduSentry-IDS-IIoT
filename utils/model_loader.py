from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from scipy.optimize import minimize
from scipy.stats import entropy as calc_entropy
from sklearn.covariance import LedoitWolf



def _load_json(path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
	if not os.path.exists(path):
		return default or {}
	with open(path, "r", encoding="utf-8") as handle:
		return json.load(handle)


def load_known_attacks(data_dir: str) -> List[str]:
	payload = _load_json(os.path.join(data_dir, "known_attacks_list.json"), {})
	if isinstance(payload, list):
		return payload
	return payload.get("known_attacks", [])


def load_split_info(data_dir: str) -> Dict[str, Any]:
	return _load_json(os.path.join(data_dir, "split_info.json"), {})


class GeneralizedOODDetector:
	def __init__(self, xgb_model, target_encoder):
		self.xgb_model = xgb_model
		self.target_encoder = target_encoder
		self.temperature = 1.0
		self.class_means = {}
		self.cov_inv = None

	def calibrate_temperature(self, X_train, y_train):
		unique_classes = np.unique(y_train)
		if len(unique_classes) < 2:
			return

		proba = self.xgb_model.predict_proba(X_train)

		def loss(temp):
			if temp <= 0:
				return 1e10
			scaled = proba ** (1 / temp)
			scaled = scaled / scaled.sum(axis=1, keepdims=True)
			nll = 0
			for i, y in enumerate(y_train):
				nll -= np.log(scaled[i, y] + 1e-10)
			return nll

		result = minimize(loss, x0=1.0, bounds=[(0.1, 10.0)], method="L-BFGS-B")
		self.temperature = result.x[0]

	def fit_mahalanobis(self, X_train, y_train):
		classes = np.unique(y_train)
		for cls in classes:
			X_class = X_train[y_train == cls]
			self.class_means[cls] = np.mean(X_class, axis=0)

		cov_estimator = LedoitWolf()
		cov_estimator.fit(X_train)
		self.cov_inv = np.linalg.pinv(cov_estimator.covariance_)

	def get_mahalanobis_to_class(self, X, class_idx_list):
		distances = np.zeros(len(X))
		for i in range(len(X)):
			class_idx = class_idx_list[i]
			class_name = self.target_encoder.inverse_transform([class_idx])[0]

			if class_name not in self.class_means:
				distances[i] = 999.0
				continue

			mean = self.class_means[class_name]
			x = X[i]
			diff = x - mean
			try:
				distances[i] = np.sqrt(np.dot(np.dot(diff, self.cov_inv), diff))
			except Exception:
				distances[i] = np.linalg.norm(diff)
		return distances

	def predict_with_calibration(self, X):
		raw_proba = self.xgb_model.predict_proba(X)
		calibrated = raw_proba ** (1 / self.temperature)
		calibrated = calibrated / calibrated.sum(axis=1, keepdims=True)
		return calibrated

	def get_ood_score(
		self,
		X,
		ae_errors_subset=None,
		w_mahala=0.6,
		w_ae=0.3,
		w_entropy=0.1,
	):
		calibrated_proba = self.predict_with_calibration(X)
		pred_idx = np.argmax(calibrated_proba, axis=1)

		entropy = np.array([calc_entropy(p) for p in calibrated_proba])
		norm_entropy = entropy / (np.log(calibrated_proba.shape[1]) + 1e-10)

		mahalanobis_dist = self.get_mahalanobis_to_class(X, pred_idx)
		max_mahala = np.percentile(mahalanobis_dist, 99) + 1e-10
		norm_mahalanobis = np.clip(mahalanobis_dist / max_mahala, 0, 1)

		if ae_errors_subset is not None:
			max_ae = np.percentile(ae_errors_subset, 99) + 1e-10
			norm_ae = np.clip(ae_errors_subset / max_ae, 0, 1)
		else:
			norm_ae = np.zeros(len(X))
			total = w_mahala + w_entropy
			w_mahala = w_mahala / total
			w_entropy = w_entropy / total
			w_ae = 0.0

		ood_score = w_mahala * norm_mahalanobis + w_ae * norm_ae + w_entropy * norm_entropy

		return ood_score, norm_entropy, norm_mahalanobis, calibrated_proba, pred_idx


def load_models(model_dir: str, data_dir: str) -> Dict[str, Any]:
	xgb_saved = joblib.load(os.path.join(model_dir, "xgb_hybrid_model.pkl"))
	xgb_model = xgb_saved["model"]
	target_encoder = xgb_saved["target_encoder"]

	ae_saved = joblib.load(os.path.join(model_dir, "autoencoder_hybrid_model.pkl"))
	autoencoder = ae_saved["autoencoder"]

	ae_threshold = float(ae_saved.get("threshold", 0.0))
	ae_threshold_payload = _load_json(os.path.join(data_dir, "ae_threshold.json"), {})
	if "threshold" in ae_threshold_payload:
		ae_threshold = float(ae_threshold_payload["threshold"])

	known_attacks = load_known_attacks(data_dir)
	split_info = load_split_info(data_dir)

	return {
		"xgb_saved": xgb_saved,
		"xgb_model": xgb_model,
		"target_encoder": target_encoder,
		"ae_saved": ae_saved,
		"autoencoder": autoencoder,
		"ae_threshold": ae_threshold,
		"known_attacks": known_attacks,
		"split_info": split_info,
	}
