# audio_processing.py
import numpy as np
import librosa
from scipy.ndimage import maximum_filter
import xxhash
from config import PREFERENCES  # Or import PREFERENCES from a common module

def load_audio(file_path, sr=None):
    if sr is None:
        sr = PREFERENCES["sampling_rate"]
    audio, sample_rate = librosa.load(file_path, sr=sr)
    return audio, sample_rate

def compute_spectrogram(audio, sample_rate):
    spectrogram = librosa.stft(audio)
    spectrogram_db = librosa.amplitude_to_db(np.abs(spectrogram))
    return spectrogram_db

def get_peaks(spectrogram, threshold=None):
    if threshold is None:
        threshold = PREFERENCES["loudness_gate"]
    max_filt = maximum_filter(spectrogram, size=(10, 10))
    peaks = (spectrogram == max_filt) & (spectrogram > np.percentile(spectrogram, threshold))
    peak_coords = np.column_stack(np.where(peaks))
    return peak_coords

def _generate_hashes_for_index(i, peaks, fan_value=None):
    if fan_value is None:
        fan_value = PREFERENCES["fan_value"]
    local_hashes = []
    for j in range(1, fan_value):
        if i + j < len(peaks):
            freq1, time1 = peaks[i]
            freq2, time2 = peaks[i + j]
            hash_str = f"{freq1}|{freq2}|{time2 - time1}"
            hash_val = xxhash.xxh64(hash_str.encode()).hexdigest()[:10]
            local_hashes.append((hash_val, time1))
    return local_hashes

def generate_hashes(peaks, fan_value=None):
    if fan_value is None:
        fan_value = PREFERENCES["fan_value"]
    hashes = []
    for i in range(len(peaks)):
        hashes.extend(_generate_hashes_for_index(i, peaks, fan_value))
    return hashes
