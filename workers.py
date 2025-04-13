# workers.py
import sqlite3
import os
import time
from collections import Counter
from PyQt6.QtCore import QThread, pyqtSignal
from database import DB_FILE
from audio_processing import load_audio, compute_spectrogram, get_peaks, generate_hashes

class QueryWorker(QThread):
    progress = pyqtSignal(int, int, float)  # current_count, total, estimated_remaining_sec
    result = pyqtSignal(object)             # (best_match, similar_songs)

    def __init__(self, query_file, parent=None):
        super().__init__(parent)
        self.query_file = query_file
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            audio, sr = load_audio(self.query_file)
            spectrogram = compute_spectrogram(audio, sr)
            peaks = get_peaks(spectrogram)
            hashes = generate_hashes(peaks)
            total = len(hashes)
            matches = []
            batch_size = 1000
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            start_time = time.time()
            for i in range(0, total, batch_size):
                if self._is_cancelled:
                    self.result.emit(("Cancelled", []))
                    conn.close()
                    return
                batch = hashes[i: i + batch_size]
                batch_hashes = [h for h, _ in batch]
                placeholders = ','.join('?' for _ in batch_hashes)
                query = f"SELECT song_id, time_offset FROM fingerprints WHERE hash IN ({placeholders})"
                cursor.execute(query, batch_hashes)
                batch_results = cursor.fetchall()
                matches.extend(batch_results)
                current = i + len(batch)
                elapsed = time.time() - start_time
                remaining = (elapsed / current) * (total - current) if current > 0 else 0
                self.progress.emit(current, total, remaining)
            conn.close()
            if not matches:
                self.result.emit((None, []))
                return
            song_match_counts = Counter(song_id for song_id, _ in matches)
            top_matches = song_match_counts.most_common(5)
            results = []
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            for song_id, count in top_matches:
                cursor.execute("SELECT name FROM songs WHERE id = ?", (song_id,))
                row = cursor.fetchone()
                if row:
                    results.append((row[0], count))
            conn.close()
            if results:
                best = results[0]
                similar = results[1:]
            else:
                best = None
                similar = []
            self.result.emit((best, similar))
        except Exception as e:
            self.result.emit(("Error: " + str(e), []))

class BatchWorker(QThread):
    progress = pyqtSignal(int)
    finished_signal = pyqtSignal(str)

    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.mp3')]
            total = len(files)
            if total == 0:
                self.finished_signal.emit("No MP3 files found.")
                return
            from database import insert_song, insert_fingerprints
            from audio_processing import load_audio, compute_spectrogram, get_peaks, generate_hashes
            for i, file in enumerate(files):
                if self._is_cancelled:
                    self.finished_signal.emit("Batch addition cancelled.")
                    return
                file_path = os.path.join(self.folder_path, file)
                song_name = os.path.splitext(file)[0]
                audio, sr = load_audio(file_path)
                spectrogram = compute_spectrogram(audio, sr)
                peaks = get_peaks(spectrogram)
                hashes = generate_hashes(peaks)
                song_id = insert_song(song_name)
                insert_fingerprints(song_id, hashes)
                self.progress.emit(int((i + 1) / total * 100))
            self.finished_signal.emit(f"Added {total} songs successfully.")
        except Exception as e:
            self.finished_signal.emit("Error: " + str(e))
