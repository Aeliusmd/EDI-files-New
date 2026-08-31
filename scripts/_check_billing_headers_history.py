"""Read-only check of BillingHeadersHistory 277/999 columns on Sithum DB."""
from __future__ import annotations

import pyodbc

SERVER = "10.103.0.211"
DATABASE = "ClaudMD_Development_Sithum"
USER = "testuser"
PASSWORD = "Test@123"
DRIVER = "ODBC Driver 17 for SQL Server"

COLS_WANTED = [
    "999FileHeaderId",
    "277FileHeaderId",
    "Is999FileAccepted",
    "Is277FileAccepted",
    "999FileAcceptedOrRejectedReason",
    "277FileAcceptedOrRejectedReason",
]


def main() -> None:
    conn_str = (
        f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};"
        f"UID={USER};PWD={PASSWORD};TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str, timeout=15)
    cur = conn.cursor()

    print("=== TABLES FOUND ===")
    cur.execute(
        """
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME IN (
          'BillingHeadersHistory','999FileHeader','277FileHeader',
          'Edi999File','Edi277File','Edi999Ack','Edi277Status'
        )
        ORDER BY TABLE_NAME
        """
    )
    for schema, name in cur.fetchall():
        print(f"  {schema}.{name}")

    print("\n=== BillingHeadersHistory — wanted columns ===")
    placeholders = ",".join("?" for _ in COLS_WANTED)
    cur.execute(
        f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'BillingHeadersHistory'
          AND COLUMN_NAME IN ({placeholders})
        ORDER BY COLUMN_NAME
        """,
        COLS_WANTED,
    )
    found = {row[0]: row for row in cur.fetchall()}
    missing = []
    for col in COLS_WANTED:
        if col in found:
            r = found[col]
            print(f"  EXISTS  {col}: {r[1]} nullable={r[2]} max_len={r[3]}")
        else:
            print(f"  MISSING {col}")
            missing.append(col)

    print("\n=== All BillingHeadersHistory columns ===")
    cur.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'BillingHeadersHistory'
        ORDER BY ORDINAL_POSITION
        """
    )
    for name, dtype, nullable in cur.fetchall():
        print(f"  {name} ({dtype}) nullable={nullable}")

    for table in ("999FileHeader", "277FileHeader"):
        print(f"\n=== {table} ===")
        cur.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?",
            table,
        )
        if cur.fetchone()[0]:
            cur.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
                """,
                table,
            )
            for name, dtype, nullable in cur.fetchall():
                print(f"  {name} ({dtype}) nullable={nullable}")
        else:
            print("  TABLE NOT FOUND")

    conn.close()
    print(f"\nMissing count: {len(missing)}")


if __name__ == "__main__":
    main()
