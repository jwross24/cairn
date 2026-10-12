import json
import sys
from pathlib import Path


def main():
    document = json.load(sys.stdin)
    artifact_name = document.pop("artifact_name", "output.json")
    output = {**document, "status": "OK", "candidate": False}
    print(json.dumps(output))
    artifact = Path(sys.argv[1]) / artifact_name
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps({**output, "candidate": True}))


if __name__ == "__main__":
    main()
