import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (id INTEGER PRIMARY KEY, name TEXT UNIQUE, url TEXT, area TEXT, enabled INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS stations (id INTEGER PRIMARY KEY, external_id TEXT, source_id INTEGER, name TEXT, area TEXT, province TEXT, municipality TEXT, latitude REAL, longitude REAL, elevation REAL, status TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS sensors (id INTEGER PRIMARY KEY, station_id INTEGER, external_id TEXT, sensor_type TEXT, unit TEXT, status TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS measurements (sensor_id INTEGER, observed_at TEXT, value REAL, quality TEXT, received_at TEXT, PRIMARY KEY(sensor_id, observed_at));
CREATE TABLE IF NOT EXISTS thresholds (id INTEGER PRIMARY KEY, source TEXT, sensor_external_id TEXT, station_name TEXT, sensor_type TEXT, direction TEXT DEFAULT 'above', attention REAL, prealarm REAL, alarm REAL, unit TEXT, valid_from TEXT, reference TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, event_type TEXT, severity TEXT, started_at TEXT, ended_at TEXT, source TEXT, description TEXT, geometry_wkt TEXT);
CREATE TABLE IF NOT EXISTS diagnostics (id INTEGER PRIMARY KEY, checked_at TEXT DEFAULT CURRENT_TIMESTAMP, source TEXT, status TEXT, http_code TEXT, elapsed_ms INTEGER, detail TEXT);
"""


def initialize_sqlite(path):
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    connection.commit()
    connection.close()


POSTGIS_NOTE = "PostGIS e il database operativo raccomandato. SQLite e disponibile solo come cache locale/offline nella v0.1.0."
