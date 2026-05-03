import csv
import json
import math
import os
import sys
import time
import requests
from dotenv import load_dotenv

# Allow running this file directly from the repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

load_dotenv(os.path.join(REPO_ROOT, ".env"))

from backend.src.api.models import Hospital, Scenario, VehiclePool, Depot

# =========================================
#   CONFIG
# =========================================
API_KEY = os.getenv("ORS_API_KEY", "")
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
HOSPITALS_DIR = f"{STORAGE_DIR}/hospitals"
DISTANCES_DIR = f"{STORAGE_DIR}/distances"
SCENARIOS_DIR = f"{STORAGE_DIR}/scenarios"
HOSPITAL_PREFIX = "hospital_"
SCENARIO_PREFIX = "scenario_"
INPUT_CSV = os.path.join(os.path.dirname(__file__), "Hospitals_-_HSE_Ireland.csv")
INPUT_CSV_ROWS = 132
BATCH_SIZE = 27

PROFILE = "driving-car"
MATRIX_URL = f"https://api.openrouteservice.org/v2/matrix/{PROFILE}"

SLEEP_BETWEEN_CALLS_SEC = 1
CALL_TIMEOUT_SEC = 120

mean_demand = {3: 3, 7: 3, 8: 4, 9: 6, 10: 18, 13: 5, 14: 6, 15: 7, 16: 5, 17: 4, 24: 7, 25: 2, 26: 9, 29: 9, 30: 11, 32: 20, 33: 10, 34: 2, 42: 4, 45: 5, 46: 5, 47: 18, 49: 5, 52: 2, 55: 4, 57: 13, 62: 4, 64: 17, 65: 5, 66: 14, 67: 11, 68: 8, 69: 7, 70: 7, 73: 4, 76: 7, 77: 11, 78: 2, 80: 4, 82: 12, 84: 10, 85: 4, 86: 2, 87: 8, 90: 4, 91: 9, 94: 1, 96: 3, 97: 22, 102: 1, 105: 5, 109: 14, 110: 5, 111: 5, 112: 1, 113: 3, 114: 6, 115: 7, 116: 1, 117: 18, 118: 1, 119: 3, 122: 17, 123: 9, 124: 4, 126: 8, 127: 19, 128: 15, 129: 8, 130: 6, 131: 3}
default_demand = 2
munster_ids = {43, 19, 42, 88, 80, 127, 59, 129, 8, 114, 83, 34, 111, 104, 93, 131, 128, 39, 132, 71, 44, 62, 74, 50, 72, 61, 81, 60, 53, 35, 126, 17, 20, 51, 100, 7, 106, 108, 41, 28, 6, 56, 124, 31, 110, 67, 14, 32, 33, 125}

# =========================================
#   LOAD DATA
# =========================================

if not API_KEY:
    raise RuntimeError("ORS_API_KEY is missing from the project root .env file")

points: dict[int, Hospital] = {}

def coord_float_to_e6(coord: float) -> int:
    return round(coord * 1e6)

def address_combined(*components: str) -> str:
    return ", ".join([c for c in components if c and c.strip()])

with open(INPUT_CSV, encoding="utf-8-sig") as csv_file:
    reader = csv.DictReader(csv_file)
    required_cols = {"OBJECTID", "POINT_X", "POINT_Y", "category", "subcategory", "name", "address1", "address2", "address3", "address4", "Eircode"}
    assert reader.fieldnames is not None
    for col in reader.fieldnames:
        if col in required_cols:
            required_cols.remove(col)
    if required_cols:
        raise ValueError(f"Missing required columns: {required_cols}")
    for row in reader:
        point_id = int(row["OBJECTID"])
        lng_e6 = coord_float_to_e6(float(row["POINT_X"]))
        lat_e6 = coord_float_to_e6(float(row["POINT_Y"]))
        adr = address_combined(row["address1"], row["address2"], row["address3"], row["address4"])
        points[point_id] = Hospital(
            id=point_id,
            lat_e6=lat_e6,
            lng_e6=lng_e6,
            display_lat_e6=lat_e6,
            display_lng_e6=lng_e6,
            category=row["category"],
            subcategory=row["subcategory"],
            name=row["name"],
            address=adr,
            eircode=row["Eircode"],
            demand=mean_demand.get(point_id, default_demand),
        )

ids = sorted(points.keys())
print(f"Loaded {len(points)} locations")

if len(points) != INPUT_CSV_ROWS:
    print(f"Warning: Expected {INPUT_CSV_ROWS} rows in {INPUT_CSV}, but found {len(points)}")


# =========================================
#   PREPARE OUTPUT DATA STRUCTURES
# =========================================

idx_lookup = {id: idx for idx, id in enumerate(ids)}
dist_matrix = [[math.inf] * len(points) for _ in range(len(points))]
time_matrix = [[math.inf] * len(points) for _ in range(len(points))]
for i in range(len(points)):
    dist_matrix[i][i] = 0
    time_matrix[i][i] = 0

N_POINTS = len(points)
BATCH_COUNT = (N_POINTS + BATCH_SIZE - 1) // BATCH_SIZE
print(f"Will make {BATCH_COUNT * (BATCH_COUNT - 1) // 2} calls to API")


# =========================================
#   Call matrix API for each batch pair
# =========================================

call_idx = 1
for i1 in range(BATCH_COUNT - 1):
    for i2 in range(i1 + 1, BATCH_COUNT):
        batch1_ids = ids[i1 * BATCH_SIZE: min(N_POINTS, (i1 + 1) * BATCH_SIZE)]
        batch2_ids = ids[i2 * BATCH_SIZE: min(N_POINTS, (i2 + 1) * BATCH_SIZE)]
        batch_full = batch1_ids + batch2_ids
        print(f"{call_idx}. Requesting batch {i1}_{i2} of size {len(batch_full)}")
        headers = {
            "Authorization": API_KEY,
            "Content-Type": "application/json"
        }
        locations = []
        for point_id in batch_full:
            point = points[point_id]
            locations.append([point.lng_e6 / 1e6, point.lat_e6 / 1e6])
        payload = {
            "locations":            locations,
            "metrics":              ["distance", "duration"],
            "units":                "m",        # distance in metres
            "resolve_locations":    False
        }
        response = requests.post(MATRIX_URL, headers=headers, json=payload, timeout=CALL_TIMEOUT_SEC)

        if response.status_code != 200:
            raise RuntimeError(
                f"Matrix request failed: "
                f"{response.status_code} {response.text}"
            )

        data = response.json()
        if "distances" not in data or "durations" not in data:
            raise RuntimeError(f"Unexpected API response: {data}")
        distances = data["distances"]
        n = len(distances)
        n_expected = len(batch_full)
        if n == 0 or n != len(distances[0]) or n != n_expected:
            raise RuntimeError(f"Unexpected distance matrix size: {len(distances)}x{len(distances[0])}, expected {n_expected}x{n_expected}")
        durations = data["durations"]
        if n != len(durations) or n != len(durations[0]):
            raise RuntimeError(f"Unexpected duration matrix size: {len(durations)}x{len(durations[0])}, expected {n_expected}x{n_expected}")
        for i, src_id in enumerate(batch_full):
            for j, dst_id in enumerate(batch_full):
                if i == j:
                    continue
                dist_matrix[idx_lookup[src_id]][idx_lookup[dst_id]] = distances[i][j]
                time_matrix[idx_lookup[src_id]][idx_lookup[dst_id]] = durations[i][j]
        if "sources" in data:
            for i, di in enumerate(data["sources"]):
                point = points.get(batch_full[i])
                if point is None:
                    continue
                point.display_lng_e6 = coord_float_to_e6(di["location"][0])
                point.display_lat_e6 = coord_float_to_e6(di["location"][1])
                point.snap_distance_m = float(di.get("snapped_distance", 0.0))
        call_idx += 1
        time.sleep(SLEEP_BETWEEN_CALLS_SEC)



# ========================================
#  PREPARE SCENARIOS
# ========================================

print("Generating scenarios ...")
depot_id1 = 97
depot_id2 = 31
depot1_hospital = points.get(depot_id1)
depot2_hospital = points.get(depot_id2)
vehicles = VehiclePool(capacity=60, quantity=-1)
scenarios = []

if depot1_hospital is None:
    print(f"Error: Depot hospital with id {depot_id1} not found")
else:
    depot1 = Depot.model_validate({
        **depot1_hospital.model_dump(),
        "id": 0,
        "category": "Depot",
        "name": "National Blood Centre",
        "demand": 0,
    })
    # FULL Scenario
    full_scenario = Scenario(
        id=1,
        name="All hospitals",
        description="Scenario containing all hospitals from the dataset.",
        vehicles=[vehicles],
        depots=[depot1],
        customers=[points[id] for id in ids if id in points]    
    )
    scenarios.append(full_scenario)
    # FULL Filtered Scenario
    flt_ids = [id for id in ids if id in mean_demand]
    full_flt_scenario = Scenario(
        id=2,
        name="Filtered hospitals",
        description="Scenario containing filtered hospitals from the dataset.",
        vehicles=[vehicles],
        depots=[depot1],
        customers=[points[id] for id in flt_ids if id in points]    
    )
    scenarios.append(full_flt_scenario)
    # FULL Scenario Except Munster
    main_ids = [id for id in ids if id not in munster_ids]
    main_scenario = Scenario(
        id=3,
        name="Main hospitals",
        description="Scenario containing all hospitals except those in Munster.",
        vehicles=[vehicles],
        depots=[depot1],
        customers=[points[id] for id in main_ids if id in points]    
    )
    scenarios.append(main_scenario)
    # Filtered Scenario Except Munster
    main_flt_ids = [id for id in main_ids if id in mean_demand]
    main_flt_scenario = Scenario(
        id=4,
        name="Main filtered hospitals",
        description="Scenario containing a filtered set of hospitals.",
        vehicles=[vehicles],
        depots=[depot1],
        customers=[points[id] for id in main_flt_ids if id in points]
    )
    scenarios.append(main_flt_scenario)

if depot2_hospital is None:
    print(f"Error: Depot hospital with id {depot_id2} not found")
else:
    depot2 = Depot.model_validate({
        **depot2_hospital.model_dump(),
        "id": 0,
        "category": "Depot",
        "name": "Munster Regional Transfusion Centre",
        "demand": 0,
    })
    # Munster Scenario
    munster_scenario = Scenario(
        id=5,
        name="Munster All hospitals",
        description="Scenario containing all hospitals in Munster.",
        vehicles=[vehicles],
        depots=[depot2],
        customers=[points[id] for id in munster_ids if id in points]    
    )
    scenarios.append(munster_scenario)
    # Munster Filtered Scenario
    munster_flt_ids = [id for id in munster_ids if id in mean_demand]
    munster_flt_scenario = Scenario(
        id=6,
        name="Munster Filtered hospitals",
        description="Scenario containing a filtered set of hospitals in Munster.",
        vehicles=[vehicles],
        depots=[depot2],
        customers=[points[id] for id in munster_flt_ids if id in points]
    )
    scenarios.append(munster_flt_scenario)

print(f"Generated {len(scenarios)} scenarios")


# =========================================
# SAVE OUTPUT
# =========================================

os.makedirs(HOSPITALS_DIR, exist_ok=True)
os.makedirs(DISTANCES_DIR, exist_ok=True)
os.makedirs(SCENARIOS_DIR, exist_ok=True)

print("Saving hospitals ...")
success_count, fail_count = 0, 0
for point_id, hospital in points.items():
    out_path = f"{HOSPITALS_DIR}/{HOSPITAL_PREFIX}{point_id}.json"
    with open(out_path, "w", encoding="utf-8") as out_file:
        try:
            hospital_json = hospital.model_dump_json(indent=2)
            out_file.write(hospital_json)
            success_count += 1
        except Exception as e:            
            print(f"Error saving hospital {point_id} to {out_path}: {e}")
            fail_count += 1
print(f"Finished saving hospitals. Success: {success_count}, Fail: {fail_count}")

print("Saving distances ...")
success_count, fail_count = 0, 0
for src_id, src in points.items():
    for dst_id, dst in points.items():
        if src_id == dst_id:
            continue
        name = f"{src.lat_e6}_{src.lng_e6}_{dst.lat_e6}_{dst.lng_e6}.json"
        with open(f"{DISTANCES_DIR}/{name}", "w", encoding="utf-8") as out_file:
            try:
                payload = {
                    "distance": dist_matrix[idx_lookup[src_id]][idx_lookup[dst_id]],
                    "travel_time": time_matrix[idx_lookup[src_id]][idx_lookup[dst_id]]
                }
                json.dump(payload, out_file, indent=2)
                success_count += 1
            except Exception as e:
                print(f"Error saving distance from {src_id} to {dst_id} to {name}: {e}")
                fail_count += 1
print(f"Finished saving distances. Success: {success_count}, Fail: {fail_count}")


print("Saving scenarios ...")
success_count, fail_count = 0, 0
for scenario in scenarios:
    out_path = f"{SCENARIOS_DIR}/{SCENARIO_PREFIX}{scenario.id}.json"
    with open(out_path, "w", encoding="utf-8") as out_file:
        try:
            scenario_json = scenario.model_dump_json(indent=2)
            out_file.write(scenario_json)
            success_count += 1
        except Exception as e:
            print(f"Error saving scenario {scenario.id} to {out_path}: {e}")
            fail_count += 1
print(f"Finished saving scenarios. Success: {success_count}, Fail: {fail_count}")