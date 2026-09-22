from cairn import container, lean


def test_a_bind_mount_preserves_the_host_path_representation(monkeypatch, tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    captured = []

    def run_docker(ctx, *args, timeout_s):
        captured.extend(args)
        return lean.Run(tuple(args), None, 0, "", "", 0.0)

    monkeypatch.setattr(container, "run_docker", run_docker)
    container.run(None, "image", ["true"], mounts=((alias, "/project", "readonly=false"),))
    mount = captured[captured.index("--mount") + 1]
    assert mount == f"type=bind,source={alias.absolute()},target=/project,readonly=false"
