"""Update tracker: move fiscal from pending to processed, set round_complete=true."""
import json
from datetime import datetime, timezone

TRACKER_PATH = "/Users/lucascruz/Documents/GitHub/repo_platform/docs/skill_improvement_tracker.json"

with open(TRACKER_PATH) as f:
    tracker = json.load(f)

SKILL_NAME = "fiscal"
tracker["processed"].append(SKILL_NAME)
tracker["pending"].remove(SKILL_NAME)
tracker["last_run"] = datetime.now(timezone.utc).isoformat()

if not tracker["pending"]:
    tracker["round_complete"] = True
    tracker["reports"].append({
        "round": tracker["round"],
        "completed_at": tracker["last_run"],
        "total_skills": len(tracker["processed"]),
        "note": "All 30 skills processed in round 1."
    })

with open(TRACKER_PATH, "w") as f:
    json.dump(tracker, f, indent=2)

print("Tracker updated. pending:", tracker["pending"])
print("round_complete:", tracker["round_complete"])
print("processed count:", len(tracker["processed"]))
