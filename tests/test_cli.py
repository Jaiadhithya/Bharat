from typer.testing import CliRunner

from signalcourt import __version__
from signalcourt.cli import app


def test_version():
    r = CliRunner().invoke(app, ["version"])
    assert r.exit_code == 0 and r.stdout.strip() == __version__


def test_config_digest_lists_settings():
    r = CliRunner().invoke(app, ["config-digest"])
    assert r.exit_code == 0 and "config/settings.toml" in r.stdout
