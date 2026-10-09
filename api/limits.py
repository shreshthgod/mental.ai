"""Atomic per-owner prediction limits shared by workers on one local host.

SQLite must be on a local writable filesystem shared by those workers.
Separate hosts require a deployment-level shared limiter; this is not one.
"""
import hashlib
import math
import sqlite3
import time


class Limited(RuntimeError):
    def __init__(self, retry_after):
        self.retry_after = retry_after


class PredictLimiter:
    def __init__(self, path, *, maximum=30, window=60):
        self.path, self.maximum, self.window = path, maximum, window

    def check(self, user_id, *, now=None):
        now = time.time() if now is None else now
        key = hashlib.sha256(('predict:'+user_id).encode()).hexdigest()
        with sqlite3.connect(self.path, timeout=1.0) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS limits (owner_hash TEXT PRIMARY KEY, ends REAL NOT NULL, count INTEGER NOT NULL)')
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('DELETE FROM limits WHERE ends <= ?', (now,))
            row = conn.execute('SELECT ends, count FROM limits WHERE owner_hash = ?', (key,)).fetchone()
            if row is None:
                conn.execute('INSERT INTO limits VALUES (?, ?, 1)', (key, now+self.window))
            elif row[1] >= self.maximum:
                raise Limited(max(1, math.ceil(row[0]-now)))
            else:
                conn.execute('UPDATE limits SET count = count + 1 WHERE owner_hash = ?', (key,))
