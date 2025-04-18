# TuneTracker
Know what you listen to...

TuneTracker is an open-source, offline audio recognition desktop application built with Python and PyQt6. Inspired by audio fingerprinting techniques similar to those used by Shazam, it is designed to compare short audio snippets against a local database of songs, providing fast and configurable matching.

---

## Features

- **Audio Fingerprinting:**  
  Extracts fingerprints from audio files via spectrogram analysis and peak detection. A fast, non-cryptographic hash (xxHash) is computed for each pair of spectral peaks.

- **Song Comparison:**  
  Compare a query audio clip against a local database to retrieve the best matching song along with similar candidates, based on the number of matching fingerprint hashes.

- **Batch Import:**  
  Easily add multiple songs (MP3 files) into the database in one operation.

- **History Tracking:**  
  Maintain a history of query comparisons, viewable in a dedicated History tab and manageable via the Preferences or Database Management sections.

- **Configurable Preferences:**  
  Adjust key parameters such as sampling rate, loudness gate threshold, and fan value (the number of peak pairings) via a dedicated Preferences tab. Changing preferences can trigger a complete re-hash of the database.

- **Database Management:**  
  Clear or manage the internal database of song fingerprints.

- **Portable Desktop App:**  
  Built with PyQt6, TuneTracker is designed to be cross-platform (Linux and Windows) and portable.

---

## Installation

### Requirements

- Python 3.10 or later
- Supported on both Linux and Windows

### Steps

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/Soundhunter6154/TuneTracker
    ```

2. **Create a Virtual Environment:**

    ```bash
    python -m venv venv
    ```

3. **After creation, you will also need to activate the Virtual Environment:**

    *For Linux/Mac:*
    ```bash
    source venv/bin/activate
    ```       
    
    *For Windows:*
    ```bash
    venv\Scripts\activate
    ```           

4. **Installing Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5. **Running the application:**
    ```bash
    python main.py
    ```

---

## Usage

Once the application is launched, you have several tabs to work with:

**Compare Song:**
Select a query audio file (WAV or MP3) and run a comparison. The app extracts the audio fingerprint and compares it against your database, showing the best match and similar songs.

**Batch Add Songs:**
Choose a folder that contains MP3 files. The app processes each file, computes fingerprints, and adds them to the database.

**Preferences:**
Use sliders to adjust settings such as Sampling Rate, Loudness Gate, and Fan Value. After modifying these parameters, you can opt to re-hash the entire database.

**Database Management:**
Directly clear the database if needed.

**History:**
View a history of your past song comparisons (including query file, best match, match count, and timestamp).

**Visuals:**
Visualize the spectrogram of the query file with overlaid peaks and fingerprint match highlights (green dots indicate matched peaks). Not working very well currently.


---

## Code Structure

A sample project structure is:

```plaintext
TuneTracker/
├── venv/                 # Virtual Environment
├── audio_processing.py   # Inputs Audio, Outputs Hashes
├── config.py             # Settings (Configurable from inside the app)
├── database.py           # Generates fingerprints.db
├── fingerprints.db       # Stores the hashes, and history
├── gui.py                # Frontend of the app
├── main.py               # Main entrypoint of the app
├── recordskelly.py       # Utility to quickly splice audio files in batch for testing
```
---

## Development Guidelines

**Modular Design:**
The code is split into several files for audio processing, database handling, background workers, and GUI components. 

**Multithreading:**
Long-running operations (e.g., comparing songs or batch processing) run in separate QThread workers to keep the UI responsive.

**Configuration:**
Global parameters (sampling rate, loudness gate, fan value) are stored in config.py and can be adjusted via the Preferences tab, triggering a re-hash of existing data.

**Contributing:**
Not really planning on active maintainence yet. You may fork the Repo and do your own development on it. 


---

## Future Enhancements

As I said, not planning on maintenance, but if I had to implement features, I'd look at the list below:

Implement a more robust recording capability (real-time, cancelable recording).

Improve fingerprint matching with advanced features (temporal alignment).

Add export/import functionality for the database.

Implement enhanced visualization features, such as detailed heatmaps or dynamic overlays. But before that, fix the existing one!

Enhance error handling and logging throughout the application.


---

## License

This project is licensed under the GPL-3 License.

---

## Credits

TuneTracker was developed by 'some people' for their college project. It is inspired by SeekTune and aims to provide coding understanding for such projects in Python. Nothing more, really.

---

### Happy coding!

