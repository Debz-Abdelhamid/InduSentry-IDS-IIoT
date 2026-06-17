from __future__ import annotations

from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd


def _ensure_columns(df: pd.DataFrame, columns: Iterable[str], fill_value: Any) -> pd.DataFrame:
	for col in columns:
		if col not in df.columns:
			df[col] = fill_value
	return df


def preprocess_for_autoencoder(
	df: pd.DataFrame,
	ae_saved: Dict[str, Any],
	xgb_columns_to_drop: Iterable[str] | None,
) -> np.ndarray:
	df_batch = df.copy()
	if xgb_columns_to_drop:
		df_batch = df_batch.drop(columns=list(xgb_columns_to_drop), errors="ignore")

	ae_categorical_cols: List[str] = ae_saved["categorical_cols"]
	ae_onehot_encoder = ae_saved["onehot_encoder"]
	ae_one_hot_patterns: List[str] = ae_saved.get("one_hot_patterns", [])
	ae_skewed_info: Dict[str, Dict[str, Any]] = ae_saved.get("skewed_info", {})
	ae_feature_columns: List[str] | None = ae_saved.get("feature_columns")
	ae_scaler = ae_saved["scaler"]

	df_batch = _ensure_columns(df_batch, ae_categorical_cols, "missing")
	for col in ae_categorical_cols:
		df_batch[col] = df_batch[col].fillna("missing").astype(str)

	encoded = ae_onehot_encoder.transform(df_batch[ae_categorical_cols])
	encoded_df = pd.DataFrame(
		encoded,
		columns=ae_onehot_encoder.get_feature_names_out(ae_categorical_cols),
		index=df_batch.index,
	)
	df_batch = df_batch.drop(columns=ae_categorical_cols, errors="ignore")
	df_batch = pd.concat([df_batch, encoded_df], axis=1)

	one_hot_cols = [
		col for col in df_batch.columns if any(pattern in col for pattern in ae_one_hot_patterns)
	]
	numerical_cols = [col for col in df_batch.columns if col not in one_hot_cols]

	for col in numerical_cols:
		if col in ae_skewed_info:
			info = ae_skewed_info[col]
			if info.get("needs_shift", False):
				df_batch[col] = np.log1p(df_batch[col] + info.get("shift_value", 0))
			else:
				df_batch[col] = np.log1p(df_batch[col])

	if ae_feature_columns is not None:
		df_batch = _ensure_columns(df_batch, ae_feature_columns, 0)
		df_batch = df_batch[ae_feature_columns]

	return ae_scaler.transform(df_batch)


def preprocess_for_xgboost(df: pd.DataFrame, xgb_saved: Dict[str, Any]) -> np.ndarray:
	df_batch = df.copy()
	xgb_columns_to_drop = xgb_saved.get("columns_to_drop", [])
	xgb_categorical_cols = xgb_saved.get("categorical_cols", [])
	xgb_label_encoders = xgb_saved.get("label_encoders", {})
	xgb_selected_features = xgb_saved.get("selected_features") or xgb_saved.get(
		"feature_columns", []
	)
	xgb_scaler = xgb_saved["scaler"]

	if xgb_columns_to_drop:
		df_batch = df_batch.drop(columns=list(xgb_columns_to_drop), errors="ignore")

	df_batch = _ensure_columns(df_batch, xgb_categorical_cols, "missing")
	for col in xgb_categorical_cols:
		if col in df_batch.columns and col in xgb_label_encoders:
			le = xgb_label_encoders[col]
			df_batch[col] = df_batch[col].fillna("missing").astype(str)
			unknown_mask = ~df_batch[col].isin(le.classes_)
			if unknown_mask.any():
				df_batch.loc[unknown_mask, col] = le.classes_[0]
			df_batch[col] = le.transform(df_batch[col])

	df_batch = df_batch.reindex(columns=xgb_selected_features, fill_value=0)
	return xgb_scaler.transform(df_batch)
