from __future__ import annotations

import concurrent.futures
import threading
import time

from writer.storage.database import SerializedConnection, open_and_initialize


def test_desktop_connection_serializes_concurrent_access(tmp_path) -> None:
    conn = open_and_initialize(tmp_path / "writer.db")
    assert isinstance(conn, SerializedConnection)
    conn.execute("CREATE TABLE concurrency_probe (value INTEGER NOT NULL)")
    conn.execute("INSERT INTO concurrency_probe (value) VALUES (1)")

    failures: list[Exception] = []
    barrier = threading.Barrier(8)

    def exercise_connection(worker_id: int) -> None:
        barrier.wait()
        for iteration in range(300):
            try:
                conn.execute("SELECT value FROM concurrency_probe").fetchall()
                conn.execute(
                    "UPDATE concurrency_probe SET value = value + ?",
                    ((worker_id + iteration) % 2,),
                )
            except Exception as exc:  # noqa: BLE001
                failures.append(exc)
                return

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(exercise_connection, range(8)))

    assert failures == []
    conn.close()


def test_explicit_transaction_blocks_other_threads(tmp_path) -> None:
    conn = open_and_initialize(tmp_path / "writer.db")
    conn.execute("CREATE TABLE transaction_probe (value INTEGER NOT NULL)")
    conn.execute("BEGIN")
    conn.execute("INSERT INTO transaction_probe (value) VALUES (1)")

    started = threading.Event()

    def read_rows():
        started.set()
        return conn.execute("SELECT value FROM transaction_probe").fetchall()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(read_rows)
        assert started.wait(timeout=1)
        time.sleep(0.05)
        assert not future.done()
        conn.execute("COMMIT")
        assert [row["value"] for row in future.result(timeout=1)] == [1]

    conn.close()
