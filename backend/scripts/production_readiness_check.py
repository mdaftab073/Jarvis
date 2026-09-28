import sys
from app.services.system_health_service import validate_system

def main():
    result = validate_system()
    if result.get("success"):
        print("Production readiness check passed.")
        sys.exit(0)
    else:
        print("Production readiness check failed.")
        for key, value in result.items():
            if not value:
                print(f"{key}: {value}")
        sys.exit(1)

if __name__ == "__main__":
    main()
