import dataclasses
import json
import sys
from pathlib import Path

from cairn import countedvm, pari, verifier


def _verify(instance, result):
    if result is None:
        return None
    if instance.P is not None and instance.Q is not None:
        fields = (instance.p, instance.a, instance.b, instance.n, *instance.P, *instance.Q, result)
        rc, out, err = pari.run_gp([str(verifier.SCRIPT_PATH)], verifier.render_line(fields))
    else:
        point_p = [0] if instance.P is None else list(instance.P)
        point_q = [0] if instance.Q is None else list(instance.Q)
        script = (
            f"E=ellinit([{instance.a},{instance.b}],{instance.p});"
            f"P={point_p};Q={point_q};"
            f'if(ellmul(E,Q,{instance.n})!=[0],print("FAIL nQ-not-O");quit(1));'
            f'if(ellmul(E,P,{result})!=Q,print("FAIL xP-ne-Q");quit(1));'
            'print("OK");quit(0)\n'
        )
        rc, out, err = pari.run_gp([], script)
    accepted, reason, _ = verifier.classify(rc, out, err)
    return {"accepted": accepted, "reason": reason, "rc": rc, "stdout": out, "stderr": err}


def main():
    request = json.loads(sys.stdin.read())
    if request["op"] == "build":
        binary = countedvm.build(scratch=request["scratch"])
        response = {"binary": str(binary), "digest": countedvm.file_digest(binary)}
    else:
        instance = countedvm.Instance(
            *request["instance"][:4],
            *[None if p is None else tuple(p) for p in request["instance"][4:]],
        )
        program = Path(request["program_path"]).read_text() if "program_path" in request else request["program"]
        run = countedvm.launch(
            request["binary"],
            request["digest"],
            instance,
            program,
            request["budget"],
            attempt_id=request["attempt_id"],
            scratch_dir=request["scratch"],
        )
        response = {"run": dataclasses.asdict(run), "verification": _verify(instance, run.outcome.result)}
    print(json.dumps(response))


if __name__ == "__main__":
    main()
