import requests
import time
import json

BASE = "http://127.0.0.1:5000"

def section(title):
    print("\n" + "="*70)
    print(title)
    print("="*70)

def get(endpoint):
    try:
        r = requests.get(BASE + endpoint, timeout=5)
        print(f"\n{endpoint} -> STATUS {r.status_code}")
        try:
            print(json.dumps(r.json(), indent=2))
            return r.json()
        except:
            print(r.text)
            return None
    except Exception as e:
        print(f"{endpoint} FAILED:", e)
        return None

# ---------------------------------------------------
# TEST 1 — MODEL CAPABILITY
# ---------------------------------------------------
section("TEST 1 — MODEL CAPABILITY DETECTION")
models = get("/api/system/models")

# ---------------------------------------------------
# TEST 2 — REGIME
# ---------------------------------------------------
section("TEST 2 — REGIME STATE")
regime1 = get("/api/system/regime")

print("\nWaiting 20 seconds to see if regime adapts...")
time.sleep(20)

regime2 = get("/api/system/regime")

if regime1 == regime2:
    print("\n⚠️ Regime unchanged — may not be dynamic")

# ---------------------------------------------------
# TEST 3 — SYSTEM HEALTH
# ---------------------------------------------------
section("TEST 3 — SYSTEM HEALTH")
health = get("/api/system/state")

# ---------------------------------------------------
# TEST 4 — ACCURACY LEARNING
# ---------------------------------------------------
section("TEST 4 — LEARNING FEEDBACK")

acc1 = get("/api/system/accuracy")
print("\nWaiting 60 seconds for learning update...")
time.sleep(60)
acc2 = get("/api/system/accuracy")

if acc1 == acc2:
    print("\n⚠️ Accuracy unchanged — learning may not be active")

# ---------------------------------------------------
# TEST 5 — LIVE PREDICTION RANGE
# ---------------------------------------------------
section("TEST 5 — PREDICTION BAND CHECK")

pred = get("/api/predictions/top")

if pred and pred.get("data"):
    s = pred["data"][0]
    print("\nChecking uncertainty band:")
    print("Symbol:", s.get("symbol"))
    print("Price:", s.get("price"))
    print("Target:", s.get("target"))
    print("Confidence:", s.get("confidence"))

    if "upper" not in str(s) and "lower" not in str(s):
        print("\n⚠️ No uncertainty bands detected")

print("\nAll tests executed.")
