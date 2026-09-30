import json
import sys


def main():
    document = json.load(sys.stdin)
    assert "nonce" not in document
    n = document["point"]["n"]
    control = document["control"]
    if control == "euler":
        value = n * n + n + 41
        candidate = any(value % divisor == 0 for divisor in range(2, int(value**0.5) + 1))
    elif control == "endpoint":
        candidate = (n + 1) % document["endpoint"] == 0
    elif control == "clean":
        candidate = n > document["endpoint"] - 1
    else:
        raise ValueError("unknown control")
    document.update(status="FAIL" if document["mode"] == "fail" else "OK", candidate=candidate)
    if document["mode"] == "unverified":
        document["plan_hash"] = "wrong"
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
