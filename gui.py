from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QTabWidget, QMessageBox, QSlider
)
from workers import QueryWorker, BatchWorker, RecordWorker
from config import PREFERENCES

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

#RecordTab tab to record audio via microphone

class RecordTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.recorded_file = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Status label to display recording status
        self.statusLabel = QLabel("Status: Not recording", self)
        layout.addWidget(self.statusLabel)

        # Buttons to control recording
        btn_layout = QHBoxLayout()
        self.startBtn = QPushButton("Start Recording", self)
        self.startBtn.clicked.connect(self.startRecording)
        btn_layout.addWidget(self.startBtn)
        self.stopBtn = QPushButton("Stop Recording", self)
        self.stopBtn.clicked.connect(self.stopRecording)
        btn_layout.addWidget(self.stopBtn)
        layout.addLayout(btn_layout)

        # Button to process the recorded file through the pipeline
        self.processBtn = QPushButton("Process Recording", self)
        self.processBtn.clicked.connect(self.processRecording)
        layout.addWidget(self.processBtn)

        self.setLayout(layout)

    def startRecording(self):
        self.statusLabel.setText("Recording...")
        self.worker = RecordWorker()
        self.worker.result.connect(self.recordingFinished)
        self.worker.error.connect(self.recordingError)
        self.worker.start()

    def stopRecording(self):
        if self.worker:
            self.worker.stop()
            self.statusLabel.setText("Stopping recording...")

    def recordingFinished(self, file_path):
        self.recorded_file = file_path
        self.statusLabel.setText(f"Recording saved: {file_path}")

    def recordingError(self, error_str):
        self.statusLabel.setText(f"Error: {error_str}")

    def processRecording(self):
        if not self.recorded_file:
            self.statusLabel.setText("No recorded file to process.")
            return
        # Create a QueryWorker to process the recorded file through the existing pipeline
        self.statusLabel.setText("Processing recording...")
        self.queryWorker = QueryWorker(self.recorded_file)
        self.queryWorker.progress.connect(lambda current, total, remaining:
                                          self.statusLabel.setText(f"Processing: {current}/{total}, {int(remaining)} sec left"))
        self.queryWorker.result.connect(self.processingResult)
        self.queryWorker.start()

    def processingResult(self, result):
        best, similar = result
        if best is None:
            self.statusLabel.setText("No match found for the recording.")
        elif isinstance(best, str) and best.startswith("Error:"):
            self.statusLabel.setText(best)
        elif best == "Cancelled":
            self.statusLabel.setText("Processing cancelled.")
        else:
            text = f"Best Match: {best[0]} ({best[1]} matches)."
            if similar:
                text += "\nSimilar Songs:\n"
                for song, count in similar:
                    text += f"{song} ({count} matches)\n"
            self.statusLabel.setText(text)

# MainWindow: Organizes all tabs into the main application window

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TuneTracker")
        self.resize(700, 500)
        self.tabWidget = QTabWidget()
        self.compareTab = CompareTab()
        self.batchTab = BatchTab()
        self.preferencesTab = PreferencesTab()
        self.databaseTab = DatabaseTab()
        self.recordTab = RecordTab()
        self.tabWidget.addTab(self.compareTab, "Compare Song")
        self.tabWidget.addTab(self.batchTab, "Batch Add Songs")
        self.tabWidget.addTab(self.preferencesTab, "Preferences")
        self.tabWidget.addTab(self.databaseTab, "Database Management")
        self.tabWidget.addTab(self.recordTab, "Record")
        self.setCentralWidget(self.tabWidget)
