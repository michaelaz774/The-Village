# Parkinson's Disease Voice Detection
# This module contains the ML model and feature extraction for Parkinson's detection

import numpy as np
import librosa
import pickle
import tempfile
import os
import scipy.stats
from typing import Dict
from pydub import AudioSegment
import io

# Load trained model and scaler
MODEL_PATH = os.path.join(os.path.dirname(__file__), "best_pd_model.pkl")

try:
    with open(MODEL_PATH, "rb") as f:
        model_data = pickle.load(f)
        model = model_data["model"]
        scaler = model_data["scaler"]
        selected_features = model_data["selected_features"]
    print("✅ Parkinson's model and scaler loaded.")
except Exception as e:
    raise RuntimeError(f"Failed to load Parkinson's model: {e}")

def convert_to_wav(audio_bytes: bytes, original_format: str) -> bytes:
    """Convert uploaded audio to WAV using pydub."""
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=original_format)
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        return wav_io.getvalue()
    except Exception as e:
        raise ValueError(f"Conversion failed: {e}")

def extract_features(y: np.ndarray, sr: int) -> Dict[str, float]:
    """Extract features for Parkinson's classification."""
    features = {}

    pitches = librosa.yin(y, fmin=75, fmax=600)
    pitches = pitches[~np.isnan(pitches)]
    features["Fo"] = np.mean(pitches) if len(pitches) > 0 else 0

    if len(pitches) > 1:
        abs_diff = np.abs(np.diff(pitches))
        features["Jitter"] = np.mean(abs_diff) / (features["Fo"] + 1e-6)
    else:
        features["Jitter"] = 0

    rms = librosa.feature.rms(y=y)[0]
    if len(rms) > 1:
        abs_diff = np.abs(np.diff(rms))
        features["Shimmer"] = np.mean(abs_diff) / (np.mean(rms) + 1e-6)
        features["Shimmer(dB)"] = 20 * np.log10(features["Shimmer"] + 1e-6)
        features["Shimmer:APQ5"] = features["Shimmer"] * 0.8
        features["Shimmer:APQ11"] = features["Shimmer"] * 0.6
    else:
        features["Shimmer"] = 0
        features["Shimmer(dB)"] = 0
        features["Shimmer:APQ5"] = 0
        features["Shimmer:APQ11"] = 0

    harmonic = librosa.effects.harmonic(y)
    percussive = librosa.effects.percussive(y)
    features["HNR"] = np.mean(harmonic) / (np.mean(percussive) + 1e-6)
    features["NHR"] = 1.0 / (features["HNR"] + 1e-6)
    features["RPDE"] = scipy.stats.entropy(np.abs(librosa.stft(y).mean(axis=0)) + 1e-6)
    features["DFA"] = np.mean(np.abs(np.diff(y)))
    features["PPE"] = scipy.stats.entropy(np.abs(y) + 1e-6)
    features["spread1"] = np.std(y)
    features["spread2"] = scipy.stats.kurtosis(y)

    return features

def predict_parkinson(audio_bytes: bytes, filename: str):
    """Predict Parkinson's from audio bytes."""
    try:
        valid_exts = ('.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac', '.webm')
        if not filename.lower().endswith(valid_exts):
            raise ValueError("Unsupported audio format.")

        if len(audio_bytes) < 1024:
            raise ValueError("File too short or empty.")

        ext = os.path.splitext(filename)[1].lower()
        if ext != '.wav':
            audio_bytes = convert_to_wav(audio_bytes, ext[1:])

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            y, sr = librosa.load(tmp_path, sr=22050)
            if len(y) < sr * 3:
                raise ValueError("Recording too short (min 3 seconds).")

            all_features = extract_features(y, sr)
            missing = set(selected_features) - set(all_features.keys())
            if missing:
                raise RuntimeError(f"Missing features: {missing}")

            X = np.array([all_features[f] for f in selected_features]).reshape(1, -1)
            X_scaled = scaler.transform(X)

            proba = model.predict_proba(X_scaled)[0]
            parkinson_prob = float(proba[1])
            healthy_prob = float(proba[0])
            threshold = 0.7
            pred = 1 if parkinson_prob >= threshold else 0
            confidence = parkinson_prob if pred == 1 else healthy_prob

            result = {
                "disease": "Parkinson" if pred == 1 else "Healthy",
                "confidence": round(confidence, 3),
                "message": "Potential Parkinson's detected" if pred == 1 else "No signs of Parkinson's detected",
                "details": {
                    "parkinson_prob": round(parkinson_prob, 3),
                    "healthy_prob": round(healthy_prob, 3),
                    "features_used": selected_features
                }
            }

            if confidence < 0.7:
                result["warning"] = "Low confidence result – please test again with a longer or clearer recording."

            return result

        finally:
            os.remove(tmp_path)

    except Exception as e:
        raise RuntimeError(f"Prediction error: {e}")