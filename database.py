# database.py
import sqlite3
from collections import Counter

DB_FILE = "fingerprints.db"

def create_tables():
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON fingerprints (hash)")
    conn.commit()
    conn.close()
    # Now create the history table
    create_history_table()

def clear_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fingerprints")
    cursor.execute("DELETE FROM songs")
    conn.commit()
    conn.close()

def insert_song(name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO songs (name) VALUES (?)", (name,))
    song_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return song_id

def insert_fingerprints(song_id, hashes):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.executemany("INSERT INTO fingerprints (hash, song_id, time_offset) VALUES (?, ?, ?)",
                       [(h, song_id, t) for h, t in hashes])
    conn.commit()
    conn.close()

def find_matches_batch(hashes, batch_size=1000):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    total = len(hashes)
    import time
    start_time = time.time()
    matches = []
    for i in range(0, total, batch_size):
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
        yield current, total, remaining, matches
    conn.close()

def best_matches(hashes, top_n=5):
    last = None
    for progress_data in find_matches_batch(hashes):
        last = progress_data
    if last is None:
        return []
    matches = last[3]
    if not matches:
        return []
    song_match_counts = Counter(song_id for song_id, _ in matches)
    top = song_match_counts.most_common(top_n)
    results = []
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for song_id, count in top:
        cursor.execute("SELECT name FROM songs WHERE id = ?", (song_id,))
        row = cursor.fetchone()
        if row:
            results.append((row[0], count))
    conn.close()
    return results


# --- History Functions ---
def create_history_table():
    """Create a table to store query history, if it does not already exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_file TEXT,
            best_match TEXT,
            match_count INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_history(query_file, best_match, match_count):
    """Insert a record into the history table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO history (query_file, best_match, match_count)
        VALUES (?, ?, ?)
    """, (query_file, best_match, match_count))
    conn.commit()
    conn.close()

def get_history():
    """Retrieve all history records, most recent first."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT query_file, best_match, match_count, timestamp
        FROM history
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def clear_history():
    """Clear the history table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history")
    conn.commit()
    conn.close()
