from cairn import pari

VENDORED_F5 = ([-3, 1], 5, 7)


def test_cypari2_ellcard_on_vendored_f5_curve():
    coeffs, p, order = VENDORED_F5
    assert int(pari.ellcard(pari.pari.ellinit(coeffs, p))) == order


def test_gp_subprocess_prints_vendored_order():
    rc, out, err = pari.run_gp([], "print(ellcard(ellinit([-3,1],5)))")
    assert (rc, out.strip(), err) == (0, "7", "")


def test_curve60_vector_matches_live_gp(assert_golden):
    rc, out, err = pari.run_gp(["tests/vectors/gen60.gp"], "")
    assert (rc, err) == (0, "")
    assert_golden("curve60_seed1.json", out)


def test_curve60_vector_is_the_probed_known_answer(load_vector):
    v = load_vector("curve60_seed1.json")
    assert v["tries"] == 46
    assert (v["p"], v["a"], v["b"], v["n"]) == (
        "866004983247663323",
        "645824996691681933",
        "382308953708622014",
        "866004982950395713",
    )
    assert v["P"] == ["258236120896152398", "475063108841005863"]


def test_curve60_ellcard_under_64mb_stack(load_vector):
    v = load_vector("curve60_seed1.json")
    E = pari.pari.ellinit([int(v["a"]), int(v["b"])], int(v["p"]))
    assert str(pari.ellcard(E)) == v["n"]
    rc, out, err = pari.run_gp([], f"print(ellcard(ellinit([{v['a']},{v['b']}],{v['p']})))", stack="64M")
    assert (rc, out.strip(), err) == (0, v["n"], "")


def test_curve60_ellcard_under_8mb_default_stack_overflows_with_rc0(load_vector):
    v = load_vector("curve60_seed1.json")
    rc, out, err = pari.run_gp([], f"print(ellcard(ellinit([{v['a']},{v['b']}],{v['p']})))", stack="8M")
    assert rc == 0
    assert out.strip() == ""
    assert "stack overflows" in err
