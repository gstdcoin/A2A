"""
OfflineQueue — SQLite-backed local task queue for autonomous node operation.

When the GSTD platform is unreachable, tasks are queued locally and
executed from the local queue. Results are submitted when connectivity
is restored.

Steiniger principle: node must function autonomously even when isolated.
"""

import os
import json
import time
import sqlite3
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / '.gstd' / 'offline_queue.db'


class OfflineQueue:
    """
    Thread-safe SQLite queue for training tasks.
    Falls back to in-memory if SQLite unavailable.

    Usage:
        q = OfflineQueue()
        q.enqueue('finetune', {'job_id': 'j1', ...}, priority=10)
        task = q.dequeue('finetune')
        q.complete(task['id'], result)
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._memory: List[Dict] = []  # fallback
        self._use_sqlite = True
        self._init_db()

    def _init_db(self):
        try:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    created_at REAL NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    last_attempt REAL,
                    status TEXT DEFAULT 'pending',
                    result TEXT
                )
            """)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority DESC, created_at ASC)")
            self._conn.commit()
            logger.info(f"OfflineQueue: SQLite ready at {self.db_path}")
        except Exception as e:
            logger.warning(f"OfflineQueue: SQLite unavailable ({e}), using in-memory fallback")
            self._use_sqlite = False

    def enqueue(self, task_type: str, payload: Dict[str, Any], priority: int = 5, task_id: Optional[str] = None) -> str:
        """Add a task to the queue. Returns task ID."""
        import uuid
        tid = task_id or str(uuid.uuid4())
        payload_str = json.dumps(payload)
        now = time.time()

        with self._lock:
            if self._use_sqlite and self._conn:
                try:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO tasks (id, type, payload, priority, created_at) VALUES (?, ?, ?, ?, ?)",
                        (tid, task_type, payload_str, priority, now)
                    )
                    self._conn.commit()
                except Exception as e:
                    logger.error(f"OfflineQueue enqueue error: {e}")
            else:
                self._memory.append({
                    'id': tid, 'type': task_type, 'payload': payload_str,
                    'priority': priority, 'created_at': now,
                    'attempts': 0, 'last_attempt': None,
                    'status': 'pending', 'result': None,
                })
        return tid

    def dequeue(self, task_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get and lock the highest-priority pending task."""
        with self._lock:
            if self._use_sqlite and self._conn:
                try:
                    query = "SELECT * FROM tasks WHERE status = 'pending'"
                    params: tuple = ()
                    if task_type:
                        query += " AND type = ?"
                        params = (task_type,)
                    query += " ORDER BY priority DESC, created_at ASC LIMIT 1"
                    row = self._conn.execute(query, params).fetchone()
                    if not row:
                        return None
                    cols = [d[0] for d in self._conn.execute(query, params).description] if False else \
                           ['id', 'type', 'payload', 'priority', 'created_at', 'attempts', 'last_attempt', 'status', 'result']
                    task = dict(zip(cols, row))
                    self._conn.execute(
                        "UPDATE tasks SET status='running', attempts=attempts+1, last_attempt=? WHERE id=?",
                        (time.time(), task['id'])
                    )
                    self._conn.commit()
                    task['payload'] = json.loads(task['payload'])
                    return task
                except Exception as e:
                    logger.error(f"OfflineQueue dequeue error: {e}")
                    return None
            else:
                for task in sorted(self._memory, key=lambda t: (-t['priority'], t['created_at'])):
                    if task['status'] == 'pending' and (not task_type or task['type'] == task_type):
                        task['status'] = 'running'
                        task['attempts'] += 1
                        task['last_attempt'] = time.time()
                        return {**task, 'payload': json.loads(task['payload'])}
                return None

    def complete(self, task_id: str, result: Any) -> None:
        result_str = json.dumps(result) if not isinstance(result, str) else result
        with self._lock:
            if self._use_sqlite and self._conn:
                try:
                    self._conn.execute(
                        "UPDATE tasks SET status='done', result=? WHERE id=?",
                        (result_str, task_id)
                    )
                    self._conn.commit()
                except Exception as e:
                    logger.error(f"OfflineQueue complete error: {e}")
            else:
                for task in self._memory:
                    if task['id'] == task_id:
                        task['status'] = 'done'
                        task['result'] = result_str

    def fail(self, task_id: str, error: str, max_retries: int = 3) -> None:
        with self._lock:
            if self._use_sqlite and self._conn:
                try:
                    row = self._conn.execute("SELECT attempts FROM tasks WHERE id=?", (task_id,)).fetchone()
                    attempts = row[0] if row else 0
                    new_status = 'failed' if attempts >= max_retries else 'pending'
                    self._conn.execute(
                        "UPDATE tasks SET status=?, result=? WHERE id=?",
                        (new_status, error, task_id)
                    )
                    self._conn.commit()
                except Exception as e:
                    logger.error(f"OfflineQueue fail error: {e}")
            else:
                for task in self._memory:
                    if task['id'] == task_id:
                        task['status'] = 'failed' if task['attempts'] >= max_retries else 'pending'
                        task['result'] = error

    def pending_count(self, task_type: Optional[str] = None) -> int:
        with self._lock:
            if self._use_sqlite and self._conn:
                try:
                    if task_type:
                        return self._conn.execute(
                            "SELECT COUNT(*) FROM tasks WHERE status='pending' AND type=?", (task_type,)
                        ).fetchone()[0]
                    return self._conn.execute(
                        "SELECT COUNT(*) FROM tasks WHERE status='pending'"
                    ).fetchone()[0]
                except Exception:
                    return 0
            return sum(1 for t in self._memory
                      if t['status'] == 'pending' and (not task_type or t['type'] == task_type))

    def done_results(self) -> List[Dict[str, Any]]:
        """Get completed tasks whose results haven't been submitted yet."""
        with self._lock:
            if self._use_sqlite and self._conn:
                try:
                    rows = self._conn.execute("SELECT * FROM tasks WHERE status='done'").fetchall()
                    cols = ['id', 'type', 'payload', 'priority', 'created_at', 'attempts', 'last_attempt', 'status', 'result']
                    return [dict(zip(cols, row)) for row in rows]
                except Exception:
                    return []
            return [t for t in self._memory if t['status'] == 'done']

    def delete(self, task_id: str) -> None:
        with self._lock:
            if self._use_sqlite and self._conn:
                try:
                    self._conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
                    self._conn.commit()
                except Exception:
                    pass
            else:
                self._memory = [t for t in self._memory if t['id'] != task_id]

    def close(self):
        if self._conn:
            self._conn.close()
