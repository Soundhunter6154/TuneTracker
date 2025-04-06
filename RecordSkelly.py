import os
import sqlite3
import wave
from collections import Counter
import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
from scipy.ndimage import maximum_filter
import xxhash  # Fast non-cryptographic hash
from tqdm import tqdm
import concurrent.futures

# For microphone recording and conversion
import pyaudio  # To record audio
from pydub import AudioSegment  # To convert WAV to MP3

# ========== CONFIGURABLE PARAMETERS ==========
SAMPLING_RATE = 16000        # Sample rate for audio recording and processing
HASH_FAN_VALUE = 5           # Number of peaks to pair for hash generation
RECORD_DURATION = 5          # Duration in seconds for microphone recording
TEMP_WAV_FILE = "temp_recording.wav"  # Temporary file name for the recorded WAV
TEMP_MP3_FILE = "temp_recording.mp3"  # Temporary file name for the converted MP3
DB_FILE = "fingerprints.db"  # Database file name

# ========== Audio Processing Functions ==========

def load_audio(file_path, sr=SAMPLING_RATE):
    """Load an audio file and return its waveform and sample rate."""
    audio, sample_rate = librosa.load(file_path, sr=sr)
    return audio, sample_rate

def compute_spectrogram(audio, sample_rate):
    """Compute and return a spectrogram of the audio."""
    spectrogram = librosa.stft(audio)
    spectrogram_db = librosa.amplitude_to_db(np.abs(spectrogram))
    return spectrogram_db

# ========== Fingerprinting Functions ==========

def get_peaks(spectrogram, threshold=10):
    """Identify peaks in the spectrogram using a max filter."""
    max_filt = maximum_filter(spectrogram, size=(10, 10))
    peaks = (spectrogram == max_filt) & (spectrogram > np.percentile(spectrogram, threshold))
    peak_coords = np.column_stack(np.where(peaks))
    return peak_coords

def _generate_hashes_for_index(i, peaks, fan_value):
    """Helper function for parallel hash generation for a given index."""
    local_hashes = []
    for j in range(1, fan_value):
        if i + j < len(peaks):
            freq1, time1 = peaks[i]
            freq2, time2 = peaks[i + j]
            hash_str = f"{freq1}|{freq2}|{time2 - time1}"
            # Use xxHash for fast non-cryptographic hashing; truncate to 10 characters.
            hash_val = xxhash.xxh64(hash_str.encode()).hexdigest()[:10]
            local_hashes.append((hash_val, time1))
    return local_hashes

def generate_hashes(peaks, fan_value=HASH_FAN_VALUE):
    """Generate hashes from peaks by pairing them using parallel processing."""
    hashes = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(_generate_hashes_for_index, i, peaks, fan_value) for i in range(len(peaks))]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Generating hashes", unit="index"):
            hashes.extend(future.result())
    return hashes

# ========== Database Functions ==========

def create_tables():
    """Create the database tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fingerprints (
        hash TEXT,
        song_id INTEGER,
        time_offset INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)
    conn.commit()
    conn.close()

def insert_song(name):
    """Insert a new song into the database and return its ID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO songs (name) VALUES (?)", (name,))
    song_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return song_id

def insert_fingerprints(song_id, hashes):
    """Store the fingerprints of a song."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO fingerprints (hash, song_id, time_offset) VALUES (?, ?, ?)",
        [(h, song_id, t) for h, t in hashes]
    )
    conn.commit()
    conn.close()

def find_matches(hashes):
    """Find matching hashes in the database with a progress bar."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = "SELECT song_id, time_offset FROM fingerprints WHERE hash = ?"
    matches = []
    for h, _ in tqdm(hashes, desc="Searching database", unit="hash"):
        cursor.execute(query, (h,))
        matches.extend(cursor.fetchall())
    conn.close()
    return matches

def best_matches(hashes, top_n=3):
    """Return the top N matching songs with the count of matching hashes."""
    matches = find_matches(hashes)
    if not matches:
        return []
    song_match_counts = Counter(song_id for song_id, _ in matches)
    top_matches = song_match_counts.most_common(top_n)
    results = []
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for song_id, count in top_matches:
        cursor.execute("SELECT name FROM songs WHERE id = ?", (song_id,))
        row = cursor.fetchone()
        if row:
            results.append((row[0], count))
    conn.close()
    return results

# ========== Compare Song Function ==========

def compare_song(file_path):
    """Compare an audio file against the database and display the top 3 matches."""
    try:
        audio, sr = load_audio(file_path)
        spectrogram = compute_spectrogram(audio, sr)
        peaks = get_peaks(spectrogram)
        hashes = generate_hashes(peaks)
        results = best_matches(hashes, top_n=3)
        if results:
            print("\nTop matches:")
            for song_name, count in results:
                print(f"  {song_name}: {count} matching hashes")
        else:
            print("No matches found.")
    except Exception as e:
        print(f"Error processing the file: {e}")

# ========== Microphone Recording Functions ==========

def list_input_devices():
    """List available microphone devices."""
    pa = pyaudio.PyAudio()
    device_count = pa.get_device_count()
    devices = []
    for i in range(device_count):
        info = pa.get_device_info_by_index(i)
        if info.get('maxInputChannels', 0) > 0:
            devices.append((i, info.get('name')))
    pa.terminate()
    return devices

def record_audio(device_index, duration=RECORD_DURATION, rate=SAMPLING_RATE, output_wav=TEMP_WAV_FILE):
    """
    Record audio from the specified microphone device for a given duration,
    and save it as a WAV file.
    """
    pa = pyaudio.PyAudio()
    # Set up stream parameters
    channels = 1
    format = pyaudio.paInt16
    frames_per_buffer = 1024

    stream = pa.open(format=format,
                     channels=channels,
                     rate=rate,
                     input=True,
                     input_device_index=device_index,
                     frames_per_buffer=frames_per_buffer)

    print(f"Recording for {duration} seconds...")
    frames = []
    for _ in range(0, int(rate / frames_per_buffer * duration)):
        data = stream.read(frames_per_buffer)
        frames.append(data)
    print("Recording finished.")

    stream.stop_stream()
    stream.close()
    pa.terminate()

    # Write frames to a WAV file
    wf = wave.open(output_wav, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(pa.get_sample_size(format))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()

def convert_wav_to_mp3(input_wav=TEMP_WAV_FILE, output_mp3=TEMP_MP3_FILE):
    """Convert a WAV file to MP3 using pydub."""
    try:
        sound = AudioSegment.from_wav(input_wav)
        sound.export(output_mp3, format="mp3")
        print(f"Converted {input_wav} to {output_mp3}.")
    except Exception as e:
        print(f"Error converting WAV to MP3: {e}")

def record_and_compare():
    """Record audio from the microphone, convert it to MP3, then run the fingerprint matching pipeline."""
    devices = list_input_devices()
    if not devices:
        print("No microphone input devices found!")
        return

    print("Available input devices:")
    for idx, name in devices:
        print(f"  {idx}: {name}")

    try:
        device_index = int(input("Enter the device index you want to use: ").strip())
    except ValueError:
        print("Invalid input. Using default device (index 0).")
        device_index = 0

    try:
        duration = float(input(f"Enter recording duration in seconds (default {RECORD_DURATION}): ").strip() or RECORD_DURATION)
    except ValueError:
        duration = RECORD_DURATION

    # Record audio to a temporary WAV file
    record_audio(device_index, duration=duration)
    # Convert recorded WAV to MP3
    convert_wav_to_mp3()
    # Run the matching pipeline on the converted MP3
    print("Comparing recorded audio to the database...")
    compare_song(TEMP_MP3_FILE)

# ========== Menu Driven Interface ==========

def main_menu():
    create_tables()  # Ensure database and tables exist
    while True:
        print("\n==== Audio Fingerprinting Menu ====")
        print("1. Batch-add MP3 files to the database")
        print("2. Compare a query audio file to the database")
        print("3. Record audio from microphone and compare")
        print("0. Exit")
        choice = input("Enter your choice: ").strip()
        if choice == "1":
            dir_path = input("Enter the directory path containing MP3 files: ").strip()
            if os.path.isdir(dir_path):
                for file in os.listdir(dir_path):
                    if file.lower().endswith(".mp3"):
                        file_path = os.path.join(dir_path, file)
                        song_name = os.path.splitext(file)[0]
                        print(f"\nProcessing: {song_name} ...")
                        try:
                            audio, sr = load_audio(file_path)
                            spectrogram = compute_spectrogram(audio, sr)
                            peaks = get_peaks(spectrogram)
                            hashes = generate_hashes(peaks)
                            song_id = insert_song(song_name)
                            insert_fingerprints(song_id, hashes)
                            print(f"Stored {len(hashes)} hashes for '{song_name}'.")
                        except Exception as e:
                            print(f"Error processing {song_name}: {e}")
            else:
                print("Directory not found!")
        elif choice == "2":
            file_path = input("Enter the file path for the query audio: ").strip()
            if os.path.exists(file_path):
                compare_song(file_path)
            else:
                print("File not found!")
        elif choice == "3":
            record_and_compare()
        elif choice == "0":
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please try again.")

# ========== Main Entry Point ==========

if __name__ == "__main__":
    main_menu()
