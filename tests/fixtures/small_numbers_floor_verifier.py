import json
import math
import sys


def main():
    document = json.load(sys.stdin)
    assert "nonce" not in document
    n = document["point"]["n"]
    if document["control"] == "euler":
        value = n * n + n + 41
        valid = any(value % divisor == 0 for divisor in range(2, math.isqrt(value) + 1))
    elif document["control"] == "endpoint":
        valid = (n + 1) % document["endpoint"] == 0
    elif document["control"] == "clean":
        valid = n >= document["endpoint"]
    else:
        raise ValueError("unknown control")
    document.update(status="OK", counterexample_valid=valid)
    print(json.dumps(document, sort_keys=True))


if __name__ == "__main__":
    main()
