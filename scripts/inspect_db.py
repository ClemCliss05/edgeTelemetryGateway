import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry.db"


def main():
    parser = argparse.ArgumentParser(description="Inspecter la base SQLite du gateway")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Nombre de mesures à afficher (défaut : 10)",
    )
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit doit être supérieur ou égal à 1")

    if not DB_PATH.exists():
        print(f"Base de données introuvable : {DB_PATH}")
        return

    # mode=ro ouvre la base en lecture seule : le script ne peut pas la modifier.
    connection = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row

    try:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        print(f"Base : {DB_PATH}")
        print("\nTables :", ", ".join(row["name"] for row in tables))

        columns = connection.execute("PRAGMA table_info(telemetry)").fetchall()
        if not columns:
            print("La table telemetry n'existe pas.")
            return

        print("\nColonnes de telemetry :")
        for column in columns:
            print(f"  {column['name']} ({column['type']})")

        count = connection.execute(
            "SELECT COUNT(*) FROM telemetry"
        ).fetchone()[0]
        print(f"\nNombre total de mesures : {count}")

        rows = connection.execute(
            """
            SELECT id, device_id, timestamp, temperature, humidity, received_at
            FROM telemetry
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (args.limit,),
        ).fetchall()

        if not rows:
            print("Aucune mesure enregistrée.")
            return

        headers = list(rows[0].keys())
        values = [[str(row[h]) for h in headers] for row in rows]
        widths = [
            max(len(headers[i]), *(len(row[i]) for row in values))
            for i in range(len(headers))
        ]

        print(f"\nDernières mesures (maximum {args.limit}) :")
        print(" | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
        print("-+-".join("-" * width for width in widths))

        for row in values:
            print(" | ".join(row[i].ljust(widths[i]) for i in range(len(headers))))

    finally:
        connection.close()


if __name__ == "__main__":
    main()
