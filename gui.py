import sqlite3
import numpy as np
import librosa
import librosa.display
import xxhash
from matplotlib.figure import Figure

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from config import PREFERENCES  # Assuming global preferences are moved to config.py
from database import DB_FILE

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QTabWidget, QMessageBox, QSlider, QListWidget
)
from workers import QueryWorker, BatchWorker

# Compare Tab: Allows a user to select a query file, compare it, and view results
class CompareTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        self.queryLineEdit = QLineEdit(self)
        self.queryLineEdit.setPlaceholderText("Select query audio file...")
        self.selectQueryBtn = QPushButton("Browse", self)
        self.selectQueryBtn.clicked.connect(self.browseQueryFile)
        h_layout.addWidget(self.queryLineEdit)
        h_layout.addWidget(self.selectQueryBtn)
        layout.addLayout(h_layout)

        btn_layout = QHBoxLayout()
        self.compareBtn = QPushButton("Compare", self)
        self.compareBtn.clicked.connect(self.compareQuery)
        btn_layout.addWidget(self.compareBtn)
        self.cancelBtn = QPushButton("Cancel", self)
        self.cancelBtn.clicked.connect(self.cancelQuery)
        btn_layout.addWidget(self.cancelBtn)
        layout.addLayout(btn_layout)

        self.progressBar = QProgressBar(self)
        layout.addWidget(self.progressBar)
        self.progressLabel = QLabel("Progress: 0/0, Remaining: 0 sec", self)
        layout.addWidget(self.progressLabel)

        self.resultLabel = QLabel("Results will appear here.", self)
        layout.addWidget(self.resultLabel)
        self.setLayout(layout)

    def browseQueryFile(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Query Audio", "", "Audio Files (*.wav *.mp3)")
        if file:
            self.queryLineEdit.setText(file)

    def compareQuery(self):
        query_file = self.queryLineEdit.text()
        if not query_file:
            self.resultLabel.setText("Please select a query audio file.")
            return
        self.progressBar.setValue(0)
        self.progressLabel.setText("Progress: 0/0, Remaining: 0 sec")
        self.resultLabel.setText("")
        self.worker = QueryWorker(query_file)
        self.worker.progress.connect(self.updateProgress)
        self.worker.result.connect(self.displayResult)
        self.worker.start()

    def updateProgress(self, current, total, remaining):
        self.progressBar.setMaximum(total)
        self.progressBar.setValue(current)
        self.progressLabel.setText(f"Progress: {current}/{total}, Remaining: {int(remaining)} sec")

    def cancelQuery(self):
        if self.worker:
            self.worker.cancel()
            self.resultLabel.setText("Comparison cancelled.")

    def displayResult(self, res):
        best, similar = res
        if best is None:
            self.resultLabel.setText("No match found.")
        elif isinstance(best, str) and best.startswith("Error:"):
            self.resultLabel.setText(best)
        elif best == "Cancelled":
            self.resultLabel.setText("Comparison cancelled.")
        else:
            # Save history only if there is a valid best match.
            from database import add_history
            add_history(self.queryLineEdit.text(), best[0], best[1])
            text = f"<b>Best Match:</b> {best[0]} ({best[1]} matches)<br><br>"
            if similar:
                text += "<b>Similar Songs:</b><br>"
                for song, count in similar:
                    text += f"{song} ({count} matches)<br>"
            self.resultLabel.setText(text)


# Batch Tab: Allows batch addition of MP3 files into the database
class BatchTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        self.folderLineEdit = QLineEdit(self)
        self.folderLineEdit.setPlaceholderText("Select folder containing MP3 files...")
        self.selectFolderBtn = QPushButton("Browse", self)
        self.selectFolderBtn.clicked.connect(self.browseFolder)
        h_layout.addWidget(self.folderLineEdit)
        h_layout.addWidget(self.selectFolderBtn)
        layout.addLayout(h_layout)

        self.batchAddBtn = QPushButton("Add Songs in Batch", self)
        self.batchAddBtn.clicked.connect(self.batchAdd)
        layout.addWidget(self.batchAddBtn)

        self.progressBar = QProgressBar(self)
        layout.addWidget(self.progressBar)
        self.statusLabel = QLabel("Status messages appear here.", self)
        layout.addWidget(self.statusLabel)
        self.setLayout(layout)

    def browseFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folderLineEdit.setText(folder)

    def batchAdd(self):
        folder = self.folderLineEdit.text()
        if not folder:
            self.statusLabel.setText("Please select a folder.")
            return
        self.progressBar.setValue(0)
        self.worker = BatchWorker(folder)
        self.worker.progress.connect(self.progressBar.setValue)
        self.worker.finished_signal.connect(self.displayStatus)
        self.worker.start()

    def displayStatus(self, message):
        self.statusLabel.setText(message)

# Preferences Tab: Allows user to adjust global parameters and trigger a re-hash
class PreferencesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        sr_layout = QHBoxLayout()
        self.srLabel = QLabel(f"Sampling Rate: {PREFERENCES['sampling_rate']} Hz", self)
        self.srSlider = QSlider(Qt.Orientation.Horizontal, self)
        self.srSlider.setMinimum(8000)
        self.srSlider.setMaximum(44100)
        self.srSlider.setSingleStep(1000)
        self.srSlider.setValue(PREFERENCES['sampling_rate'])
        self.srSlider.valueChanged.connect(self.updateSRLabel)
        sr_layout.addWidget(self.srLabel)
        sr_layout.addWidget(self.srSlider)
        layout.addLayout(sr_layout)

        lg_layout = QHBoxLayout()
        self.lgLabel = QLabel(f"Loudness Gate: {PREFERENCES['loudness_gate']}", self)
        self.lgSlider = QSlider(Qt.Orientation.Horizontal, self)
        self.lgSlider.setMinimum(5)
        self.lgSlider.setMaximum(50)
        self.lgSlider.setSingleStep(1)
        self.lgSlider.setValue(PREFERENCES['loudness_gate'])
        self.lgSlider.valueChanged.connect(self.updateLGLabel)
        lg_layout.addWidget(self.lgLabel)
        lg_layout.addWidget(self.lgSlider)
        layout.addLayout(lg_layout)

        fv_layout = QHBoxLayout()
        self.fvLabel = QLabel(f"Fan Value: {PREFERENCES['fan_value']}", self)
        self.fvSlider = QSlider(Qt.Orientation.Horizontal, self)
        self.fvSlider.setMinimum(2)
        self.fvSlider.setMaximum(10)
        self.fvSlider.setSingleStep(1)
        self.fvSlider.setValue(PREFERENCES['fan_value'])
        self.fvSlider.valueChanged.connect(self.updateFVLabel)
        fv_layout.addWidget(self.fvLabel)
        fv_layout.addWidget(self.fvSlider)
        layout.addLayout(fv_layout)

        self.saveBtn = QPushButton("Save and Re-hash Database", self)
        self.saveBtn.clicked.connect(self.savePreferences)
        layout.addWidget(self.saveBtn)

        self.clearHistoryBtn = QPushButton("Clear History", self)
        self.clearHistoryBtn.clicked.connect(self.clearHistory)
        layout.addWidget(self.clearHistoryBtn)

        self.hashProgressBar = QProgressBar(self)
        layout.addWidget(self.hashProgressBar)
        self.hashStatusLabel = QLabel("Re-hash status will appear here.", self)
        layout.addWidget(self.hashStatusLabel)
        self.setLayout(layout)

    def updateSRLabel(self, value):
        self.srLabel.setText(f"Sampling Rate: {value} Hz")

    def updateLGLabel(self, value):
        self.lgLabel.setText(f"Loudness Gate: {value}")

    def updateFVLabel(self, value):
        self.fvLabel.setText(f"Fan Value: {value}")

    def clearHistory(self):
        from database import clear_history
        clear_history()
        QMessageBox.information(self, "History Cleared", "Query history has been cleared.")

    def savePreferences(self):
        from database import clear_database
        PREFERENCES["sampling_rate"] = self.srSlider.value()
        PREFERENCES["loudness_gate"] = self.lgSlider.value()
        PREFERENCES["fan_value"] = self.fvSlider.value()
        reply = QMessageBox.question(
            self, "Re-hash Database",
            "Saving preferences will clear and re-hash the entire database.\nDo you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            folder = QFileDialog.getExistingDirectory(self, "Select Folder with MP3 Files for Re-hash")
            if folder:
                clear_database()
                self.hashProgressBar.setValue(0)
                self.hashStatusLabel.setText("Starting re-hash...")
                from workers import BatchWorker
                self.batchWorker = BatchWorker(folder)
                self.batchWorker.progress.connect(self.hashProgressBar.setValue)
                self.batchWorker.finished_signal.connect(self.hashStatusLabel.setText)
                self.batchWorker.start()
            else:
                QMessageBox.information(self, "No Folder Selected", "Re-hash cancelled because no folder was selected.")
        else:
            QMessageBox.information(self, "Preferences Saved", "Preferences updated without re-hashing.")

# Database Tab: Allows user to clear the database manually
class DatabaseTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.clearDbBtn = QPushButton("Clear Database", self)
        self.clearDbBtn.clicked.connect(self.clearDatabase)
        layout.addWidget(self.clearDbBtn)
        self.setLayout(layout)

    def clearDatabase(self):
        confirmation = QMessageBox.question(
            self,
            "Clear Database",
            "Are you sure you want to clear the entire database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            from database import clear_database
            clear_database()
            QMessageBox.information(self, "Database Cleared", "All data has been erased.")


class HistoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.historyList = QListWidget(self)
        layout.addWidget(self.historyList)

        btn_layout = QHBoxLayout()
        self.refreshBtn = QPushButton("Refresh", self)
        self.refreshBtn.clicked.connect(self.loadHistory)
        btn_layout.addWidget(self.refreshBtn)
        self.clearBtn = QPushButton("Clear History", self)
        self.clearBtn.clicked.connect(self.clearHistory)
        btn_layout.addWidget(self.clearBtn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.loadHistory()

    def loadHistory(self):
        from database import get_history
        history = get_history()
        self.historyList.clear()
        for record in history:
            query_file, best_match, match_count, timestamp = record
            self.historyList.addItem(f"{timestamp}: {query_file} => {best_match} ({match_count} matches)")

    def clearHistory(self):
        from database import clear_history
        clear_history()
        self.loadHistory()




# gui.py (add this new VisualsTab class)

def generate_hashes_with_coords(peaks, fan_value=None):
    """
    Generate hashes from peaks, returning a list of tuples: (hash, time, freq).
    Here, each hash is generated from a peak and one of the subsequent peaks.
    """
    if fan_value is None:
        fan_value = PREFERENCES["fan_value"]
    results = []
    for i in range(len(peaks)):
        freq1, time1 = peaks[i]
        for j in range(1, fan_value):
            if i + j < len(peaks):
                freq2, time2 = peaks[i + j]
                hash_str = f"{freq1}|{freq2}|{time2 - time1}"
                hash_val = xxhash.xxh64(hash_str.encode()).hexdigest()[:10]
                results.append((hash_val, time1, freq1))
    return results

def get_matched_hashes(query_hashes):
    """
    Given query_hashes as a list of (hash, time, freq) tuples,
    return a set of hash values that are found in the database.
    """
    matched = set()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    unique_hashes = list(set(h for h, t, f in query_hashes))
    if not unique_hashes:
        return matched
    placeholders = ','.join('?' for _ in unique_hashes)
    query = f"SELECT DISTINCT hash FROM fingerprints WHERE hash IN ({placeholders})"
    cursor.execute(query, unique_hashes)
    rows = cursor.fetchall()
    for row in rows:
        matched.add(row[0])
    conn.close()
    return matched

class VisualsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.query_file = None
        self.figure = Figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.loadBtn = QPushButton("Load Query File", self)
        self.loadBtn.clicked.connect(self.loadQueryFile)
        layout.addWidget(self.loadBtn)

        self.plotBtn = QPushButton("Process and Visualize", self)
        self.plotBtn.clicked.connect(self.processAndVisualize)
        layout.addWidget(self.plotBtn)

        self.statusLabel = QLabel("Status: No file loaded.", self)
        layout.addWidget(self.statusLabel)

        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def loadQueryFile(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Query Audio", "", "Audio Files (*.wav *.mp3)")
        if file:
            self.query_file = file
            self.statusLabel.setText(f"Loaded file: {file}")

    def processAndVisualize(self):
        if not self.query_file:
            self.statusLabel.setText("No query file loaded.")
            return

        # Process the query file: load audio, compute spectrogram, detect peaks.
        audio, sr = librosa.load(self.query_file, sr=PREFERENCES["sampling_rate"])
        spectrogram = librosa.amplitude_to_db(np.abs(librosa.stft(audio)))
        peaks = self.get_peaks(spectrogram, threshold=PREFERENCES["loudness_gate"])
        # Get hashes including coordinates:
        query_hashes = generate_hashes_with_coords(peaks, fan_value=PREFERENCES["fan_value"])
        matched_set = get_matched_hashes(query_hashes)

        # Prepare the figure
        self.figure.clf()
        ax = self.figure.add_subplot(111)
        # Show the spectrogram
        librosa.display.specshow(spectrogram, sr=sr, x_axis='time', y_axis='log', ax=ax, cmap='viridis')
        ax.set_title("Query Spectrogram with Peak Matches")
        # Overlay all detected peaks as small black dots
        if len(peaks) > 0:
            # peaks: each row is (freq_index, time_index)
            ax.plot(peaks[:,1], peaks[:,0], 'ko', markersize=2)
        # Overlay matched peaks in green.
        # For each tuple in query_hashes (hash, time, freq), if hash is in matched_set, plot in green.
        for h, t, f in query_hashes:
            if h in matched_set:
                ax.plot(t, f, 'go', markersize=4)
        self.canvas.draw()
        self.statusLabel.setText(f"Plotted {len(peaks)} peaks; {len(matched_set)} hashes matched.")

    def get_peaks(self, spectrogram, threshold):
        """
        A helper version of get_peaks that replicates functionality from backend but is local
        for visualization.
        """
        from scipy.ndimage import maximum_filter
        max_filt = maximum_filter(spectrogram, size=(10,10))
        peaks_bool = (spectrogram == max_filt) & (spectrogram > np.percentile(spectrogram, threshold))
        peak_coords = np.column_stack(np.where(peaks_bool))
        return peak_coords





# MainWindow: Organizes all tabs into the main application window




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SeekTune Desktop App")
        self.resize(700, 500)
        self.tabWidget = QTabWidget()
        self.compareTab = CompareTab()
        self.batchTab = BatchTab()
        self.preferencesTab = PreferencesTab()
        self.databaseTab = DatabaseTab()
        self.historyTab = HistoryTab()
        self.visualsTab = VisualsTab()
        self.tabWidget.addTab(self.compareTab, "Compare Song")
        self.tabWidget.addTab(self.batchTab, "Batch Add Songs")
        self.tabWidget.addTab(self.preferencesTab, "Preferences")
        self.tabWidget.addTab(self.databaseTab, "Database Management")
        self.tabWidget.addTab(self.historyTab, "History")
        self.tabWidget.addTab(self.visualsTab, "Visuals")
        self.setCentralWidget(self.tabWidget)
