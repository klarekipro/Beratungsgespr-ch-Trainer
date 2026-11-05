"""Small SQLite repository. The HTTP and engine layers do not depend on SQL syntax."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol


class VersionConflict(RuntimeError):
    pass


class Repository(Protocol):
    def get_company(self) -> dict: ...
    def save_company(self, company: dict) -> None: ...
    def list_scenarios(self) -> list[dict]: ...
    def get_scenario(self, scenario_id: str) -> dict | None: ...
    def save_scenario(self, scenario: dict) -> None: ...
    def delete_scenario(self, scenario_id: str) -> bool: ...
    def get_session(self, session_id: str) -> dict | None: ...
    def save_session(self, session: dict, expected_version: int | None = None) -> None: ...
    def list_sessions(self) -> list[dict]: ...


class SQLiteStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("CREATE TABLE IF NOT EXISTS documents (kind TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(kind,id))")
            con.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    @contextmanager
    def connection(self):
        con = sqlite3.connect(self.path, timeout=10)
        try:
            con.execute("PRAGMA busy_timeout=10000")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def seed(self, company: dict, scenarios: list[dict]):
        # Marker prevents intentionally deleted scenarios reappearing after restart.
        with self.connection() as con:
            if con.execute("SELECT value FROM metadata WHERE key='seed_version'").fetchone():
                return
            con.execute("INSERT OR IGNORE INTO documents VALUES ('company','main',?)", (json.dumps(company, ensure_ascii=False),))
            for item in scenarios:
                con.execute("INSERT OR IGNORE INTO documents VALUES ('scenario',?,?)", (item["id"], json.dumps(item, ensure_ascii=False)))
            con.execute("INSERT INTO metadata VALUES ('seed_version','1')")

    def _get(self, kind, identifier):
        with self.connection() as con:
            row = con.execute("SELECT data FROM documents WHERE kind=? AND id=?", (kind, identifier)).fetchone()
            return json.loads(row[0]) if row else None

    def _put(self, kind, identifier, value):
        with self.connection() as con:
            con.execute("INSERT INTO documents(kind,id,data) VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data", (kind, identifier, json.dumps(value, ensure_ascii=False)))

    def _list(self, kind):
        with self.connection() as con:
            rows = con.execute("SELECT data FROM documents WHERE kind=? ORDER BY id", (kind,)).fetchall()
            return [json.loads(row[0]) for row in rows]

    def get_company(self):
        return self._get("company", "main")

    def save_company(self, company):
        self._put("company", "main", company)

    def list_scenarios(self):
        return self._list("scenario")

    def get_scenario(self, scenario_id):
        return self._get("scenario", scenario_id)

    def save_scenario(self, scenario):
        self._put("scenario", scenario["id"], scenario)

    def delete_scenario(self, scenario_id):
        with self.connection() as con:
            cur = con.execute("DELETE FROM documents WHERE kind='scenario' AND id=?", (scenario_id,))
            return cur.rowcount > 0

    def get_session(self, session_id):
        return self._get("session", session_id)

    def save_session(self, session, expected_version=None):
        with self.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT data FROM documents WHERE kind='session' AND id=?", (session["id"],)).fetchone()
            if expected_version is not None:
                if not row or json.loads(row[0])["version"] != expected_version:
                    raise VersionConflict("Session changed")
            con.execute("INSERT INTO documents(kind,id,data) VALUES ('session',?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data", (session["id"], json.dumps(session, ensure_ascii=False)))

    def list_sessions(self):
        return sorted(self._list("session"), key=lambda x: x["updated_at"], reverse=True)
