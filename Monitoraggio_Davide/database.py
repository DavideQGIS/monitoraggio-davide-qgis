import sqlite3
from pathlib import Path
from typing import Dict, Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_info (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS sources (id INTEGER PRIMARY KEY, name TEXT UNIQUE, url TEXT, area TEXT, enabled INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS stations (id INTEGER PRIMARY KEY, external_id TEXT, source_id INTEGER, name TEXT, area TEXT, province TEXT, municipality TEXT, latitude REAL, longitude REAL, elevation REAL, status TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS sensors (id INTEGER PRIMARY KEY, station_id INTEGER, external_id TEXT, sensor_type TEXT, unit TEXT, status TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS measurements (sensor_id INTEGER, observed_at TEXT, value REAL, quality TEXT, received_at TEXT, PRIMARY KEY(sensor_id, observed_at));
CREATE TABLE IF NOT EXISTS thresholds (id INTEGER PRIMARY KEY, source TEXT, sensor_external_id TEXT, station_name TEXT, sensor_type TEXT, direction TEXT DEFAULT 'above', attention REAL, prealarm REAL, alarm REAL, unit TEXT, valid_from TEXT, reference TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, event_type TEXT, severity TEXT, started_at TEXT, ended_at TEXT, source TEXT, description TEXT, geometry_wkt TEXT);
CREATE TABLE IF NOT EXISTS radar_products (source TEXT, observed_at TEXT, filename TEXT, local_path TEXT, compressed_bytes INTEGER, received_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(source, observed_at));
CREATE TABLE IF NOT EXISTS bulletins (source TEXT, bulletin_type TEXT, external_id TEXT, published_at TEXT, valid_from TEXT, valid_to TEXT, title TEXT, url TEXT, received_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(source, bulletin_type, external_id));
CREATE TABLE IF NOT EXISTS alerts (source TEXT, external_id TEXT, risk_type TEXT, severity TEXT, published_at TEXT, valid_from TEXT, valid_to TEXT, area_code TEXT, description TEXT, received_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(source, external_id, area_code, risk_type));
CREATE TABLE IF NOT EXISTS diagnostics (id INTEGER PRIMARY KEY, checked_at TEXT DEFAULT CURRENT_TIMESTAMP, source TEXT, status TEXT, http_code TEXT, elapsed_ms INTEGER, detail TEXT);
CREATE INDEX IF NOT EXISTS idx_measurements_observed_at ON measurements(observed_at);
CREATE INDEX IF NOT EXISTS idx_diagnostics_source_checked ON diagnostics(source, checked_at);
CREATE INDEX IF NOT EXISTS idx_radar_observed_at ON radar_products(observed_at);
CREATE INDEX IF NOT EXISTS idx_alerts_validity ON alerts(valid_from, valid_to);
"""

SCHEMA_VERSION = 2


def initialize_sqlite(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    current = connection.execute("SELECT version FROM schema_info LIMIT 1").fetchone()
    if current is None:
        connection.execute("INSERT INTO schema_info(version) VALUES (?)", (SCHEMA_VERSION,))
    elif current[0] != SCHEMA_VERSION:
        connection.execute("UPDATE schema_info SET version = ?", (SCHEMA_VERSION,))
    connection.commit()
    connection.close()


def upsert_sources(path: str, sources: Iterable[Dict[str, object]]) -> None:
    initialize_sqlite(path)
    with sqlite3.connect(path) as connection:
        connection.executemany(
            """INSERT INTO sources(name, url, area, enabled) VALUES (?, ?, ?, 1)
               ON CONFLICT(name) DO UPDATE SET url=excluded.url, area=excluded.area""",
            [(item.get("name", ""), item.get("url", ""), item.get("area", "")) for item in sources],
        )


def save_diagnostic(path: str, row: Dict[str, object]) -> None:
    initialize_sqlite(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """INSERT INTO diagnostics(source, status, http_code, elapsed_ms, detail)
               VALUES (?, ?, ?, ?, ?)""",
            (row.get("source", ""), row.get("status", ""), row.get("http", ""), row.get("ms"), row.get("detail", "")),
        )


def save_radar_product(path: str, product: Dict[str, object]) -> None:
    initialize_sqlite(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """INSERT INTO radar_products(source, observed_at, filename, local_path, compressed_bytes)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(source, observed_at) DO UPDATE SET
                   filename=excluded.filename, local_path=excluded.local_path,
                   compressed_bytes=excluded.compressed_bytes, received_at=CURRENT_TIMESTAMP""",
            ("ARPA Lombardia radar", product.get("observed_at", ""), product.get("filename", ""), product.get("path", ""), product.get("compressed_bytes", 0)),
        )


def database_status(path: str) -> Dict[str, object]:
    if not path or not Path(path).is_file():
        return {"available": False, "schema_version": None, "diagnostics": 0}
    with sqlite3.connect(path) as connection:
        version = connection.execute("SELECT version FROM schema_info LIMIT 1").fetchone()
        diagnostics = connection.execute("SELECT COUNT(*) FROM diagnostics").fetchone()[0]
    return {"available": True, "schema_version": version[0] if version else None, "diagnostics": diagnostics}


POSTGIS_NOTE = "PostGIS e il database operativo raccomandato. SQLite conserva cache locale e storico diagnostico nella serie 0.7.x."
