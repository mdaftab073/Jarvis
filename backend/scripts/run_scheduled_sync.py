from app.services.connector_service import run_scheduled_syncs


def main() -> None:
    jobs = run_scheduled_syncs()
    print(f"Processed {len(jobs)} scheduled connector sync job(s)")


if __name__ == "__main__":
    main()
