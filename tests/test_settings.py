import pytest

from signalcourt import settings as s


def test_settings_toml_loads_and_validates():
    cfg = s.load_config()
    assert cfg.rank.k == 5 and cfg.panel.quarters == 20
    assert cfg.rbi_divergence.enabled is False
    assert cfg.placebo.in_time_shifts == [-4, -3, -2, 2]


def test_unknown_key_is_rejected(tmp_path):
    p = tmp_path / "settings.toml"
    p.write_text("[rank]\nk = 5\nkk = 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        s.load_config(p)


def test_rbi_divergence_refuses_to_enable_unverified(tmp_path):
    text = (s.CONFIG_DIR / "settings.toml").read_text(encoding="utf-8")
    import re
    text = re.sub(r"(\[rbi_divergence\][^\[]*?enabled\s*=\s*)false", r"\1true", text, count=1, flags=re.S)
    p = tmp_path / "settings.toml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(s.SettingsError):
        s.load_config(p)


def test_env_keys_split(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEYS", "a, b ,,c")
    env = s.Env(_env_file=None)
    assert env.keys("GROQ_API_KEYS") == ["a", "b", "c"]
    assert env.keys("MISTRAL_API_KEYS") == [] or isinstance(env.keys("MISTRAL_API_KEYS"), list)


def test_workspace_paths(tmp_path):
    ws = s.Workspace(home=tmp_path).ensure()
    assert ws.manifest_db == tmp_path / "cache" / "manifest.sqlite"
    assert ws.run_dir("r1") == tmp_path / "runs" / "r1"
    assert ws.raw.is_dir() and ws.manual.is_dir()


def test_models_yaml_roles_reference_deployments():
    m = s.load_models()
    for role, chain in m["roles"].items():
        for d in chain:
            assert d in m["deployments"], f"{role} -> unknown deployment {d}"
    for dep, row in m["deployments"].items():
        assert row[0] in m["providers"], dep


def test_registries_parse():
    for name in ["metrics.yaml", "formulas.yaml", "pairs.yaml", "angles.yaml", "alternatives.yaml",
                 "families.yaml", "sources.yaml", "subtypes.yaml", "announcement_kinds.yaml",
                 "datasets.yaml", "sections.yaml", "rbi_divergence.yaml"]:
        assert s.load_registry(name) is not None, name
    assert s.load_registry("advice_terms.txt")
    ids = [a["id"] for a in s.load_registry("angles.yaml")]
    assert ids == [f"A{i}" for i in range(1, 15)]
    assert all(d["status"] == "verify" for d in s.load_registry("datasets.yaml"))
    assert s.load_registry("rbi_divergence.yaml")["verified"] is False


def test_digest_stable_and_covers_config():
    d1, d2 = s.config_digest(), s.config_digest()
    assert d1 == d2
    assert "config/settings.toml" in d1 and "registry/metrics.yaml" in d1
