import sqlite3
import logging
from datetime import datetime
from typing import Optional
from .models import Account, AccountStatus

logger = logging.getLogger(__name__)


class AccountStore:
    """
    SQLite-backed persistent store for created accounts.
    Thread-safe with WAL mode.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._init_schema()
        self._lock = __import__("threading").Lock()

    def _init_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                email           TEXT UNIQUE NOT NULL,
                password        TEXT NOT NULL,
                first_name      TEXT DEFAULT '',
                last_name       TEXT DEFAULT '',
                gender          TEXT DEFAULT 'male',
                birth_month     TEXT DEFAULT '01',
                birth_day       TEXT DEFAULT '01',
                birth_year      TEXT DEFAULT '1990',
                zip_code        TEXT DEFAULT '',
                phone           TEXT DEFAULT '',
                status          TEXT DEFAULT 'pending',
                device_id       TEXT DEFAULT '',
                proxy           TEXT DEFAULT '',
                error_message   TEXT DEFAULT '',
                created_at      TEXT DEFAULT '',
                verified_at     TEXT DEFAULT '',
                match_id        TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);
            CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
        """)
        self._conn.commit()

    def insert(self, account: Account) -> int:
        """Insert a new account record. Returns the row ID."""
        with self._lock:
            now = datetime.utcnow().isoformat()
            if not account.created_at:
                account.created_at = now
            cur = self._conn.execute(
                """INSERT OR IGNORE INTO accounts
                   (email, password, first_name, last_name, gender,
                    birth_month, birth_day, birth_year, zip_code, phone,
                    status, device_id, proxy, error_message, created_at, match_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (account.email, account.password, account.first_name, account.last_name,
                 account.gender, account.birth_month, account.birth_day, account.birth_year,
                 account.zip_code, account.phone, account.status.value,
                 account.device_id, account.proxy, account.error_message,
                 account.created_at, account.match_id),
            )
            self._conn.commit()
            account.id = cur.lastrowid
            return account.id

    def update_status(self, account_id: int, status: AccountStatus,
                      error: str = "", match_id: str = ""):
        with self._lock:
            now = datetime.utcnow().isoformat()
            updates = ["status = ?"]
            params = [status.value]

            if error:
                updates.append("error_message = ?")
                params.append(error)
            if match_id:
                updates.append("match_id = ?")
                params.append(match_id)
            if status == AccountStatus.VERIFIED:
                updates.append("verified_at = ?")
                params.append(now)

            params.append(account_id)
            self._conn.execute(
                f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            self._conn.commit()

    def get_by_email(self, email: str) -> Optional[Account]:
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE email = ?", (email,)
        ).fetchone()
        if row:
            return self._row_to_account(row)
        return None

    def get_by_id(self, account_id: int) -> Optional[Account]:
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if row:
            return self._row_to_account(row)
        return None

    def get_pending(self, limit: int = 100) -> list[Account]:
        rows = self._conn.execute(
            "SELECT * FROM accounts WHERE status = ? ORDER BY id LIMIT ?",
            (AccountStatus.PENDING.value, limit),
        ).fetchall()
        return [self._row_to_account(r) for r in rows]

    def get_all(self, limit: int = 1000) -> list[Account]:
        rows = self._conn.execute(
            "SELECT * FROM accounts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_account(r) for r in rows]

    def count_by_status(self) -> dict:
        rows = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM accounts GROUP BY status"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def total_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

    def _row_to_account(self, row: sqlite3.Row) -> Account:
        return Account(
            id=row[0], email=row[1], password=row[2], first_name=row[3],
            last_name=row[4], gender=row[5], birth_month=row[6], birth_day=row[7],
            birth_year=row[8], zip_code=row[9], phone=row[10],
            status=AccountStatus(row[11]), device_id=row[12], proxy=row[13],
            error_message=row[14], created_at=row[15], verified_at=row[16],
            match_id=row[17],
        )

    def close(self):
        self._conn.close()
