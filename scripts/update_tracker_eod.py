"""Update tracker: move end_of_day_digest from pending to processed."""
import json
from datetime import datetime

TRACKER_PATH = "/Users/lucascruz/Documents/GitHub/repo_platform/docs/skill_improvement_tracker.json"

with open(TRACKER_PATH) as f:
    tracker = json.load(f)

skill = "end_of_day_digest"
tracker["processed"].append(skill)
tracker["pending"].remove(skill)
tracker["last_run"] = datetime.utcnow().isoformat()

with open(TRACKER_PATH, "w") as f:
    json.dump(tracker, f, indent=2)

pending_count = len(tracker["pending"])
processed_count = len(tracker["processed"])
total = pending_count + processed_count
print(f"Updated. Processed: {processed_count}/{total}. Pending: {pending_count}")
