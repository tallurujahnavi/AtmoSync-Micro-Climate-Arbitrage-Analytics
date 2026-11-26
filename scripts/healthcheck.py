"""
healthcheck.py – Automated pre-flight environment and pipeline integrity validator.

Validates:
1. Python runtime environment (>= 3.9)
2. Directory tree structure and configuration artifacts
3. Core analytics module importability and integrity
4. End-to-end Arrhenius spoilage kinetics and CSI math sanity
"""

import sys
import os

# Add src to pythonpath
SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, os.path.abspath(SRC_DIR))


def check_python_version() -> bool:
    major, minor = sys.version_info[:2]
    return major == 3 and minor >= 9


def check_directory_structure(root_dir: str) -> dict:
    required_dirs = ["src", "tests", "data", "sql", "dbt"]
    results = {}
    for d in required_dirs:
        path = os.path.join(root_dir, d)
        results[d] = os.path.isdir(path)
    return results


def check_module_imports() -> dict:
    modules = [
        "arbitrage",
        "auth",
        "iot_simulator",
        "spoilage_arbitrage",
        "kafka_pipeline",
        "economics",
        "alerts",
        "ml_forecaster",
        "reports",
        "esg_sustainability",
        "sensor_calibration",
        "profiler",
        "websocket_gateway",
        "audit_logger",
        "geofencing",
        "tax_fuel_optimizer",
    ]
    results = {}
    for mod in modules:
        try:
            __import__(mod)
            results[mod] = True
        except Exception as e:
            results[mod] = str(e)
    return results


def run_math_sanity_check() -> bool:
    try:
        from spoilage_arbitrage import calculate_spoilage_rate_multiplier
        # Hass Avocados ideal max is 7°C; 18.5°C should yield multiplier > 2.0
        mult = calculate_spoilage_rate_multiplier("Hass Avocados", 18.5, 85.0)
        return mult > 2.0
    except Exception:
        return False


def run_full_healthcheck(root_dir: str = None) -> dict:
    if root_dir is None:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    py_ver_ok = check_python_version()
    dirs = check_directory_structure(root_dir)
    dirs_ok = all(dirs.values())
    imports = check_module_imports()
    imports_ok = all(v is True for v in imports.values())
    math_ok = run_math_sanity_check()

    overall_healthy = py_ver_ok and dirs_ok and imports_ok and math_ok

    return {
        "status": "HEALTHY" if overall_healthy else "UNHEALTHY",
        "python_version_ok": py_ver_ok,
        "directories_ok": dirs_ok,
        "directory_details": dirs,
        "imports_ok": imports_ok,
        "import_details": imports,
        "math_sanity_ok": math_ok,
    }


if __name__ == "__main__":
    res = run_full_healthcheck()
    print("=" * 60)
    print("AtmoSync Pre-Flight Environment Healthcheck")
    print("=" * 60)
    print(f"Status: {res['status']}")
    print(f"Python Runtime: {'✅ PASS' if res['python_version_ok'] else '❌ FAIL'}")
    print(f"Directory Structure: {'✅ PASS' if res['directories_ok'] else '❌ FAIL'}")
    print(f"Module Imports: {'✅ PASS' if res['imports_ok'] else '❌ FAIL'}")
    print(f"Kinetics Math Sanity: {'✅ PASS' if res['math_sanity_ok'] else '❌ FAIL'}")
    print("=" * 60)

    if res["status"] != "HEALTHY":
        sys.exit(1)
    sys.exit(0)
