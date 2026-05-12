from click.testing import CliRunner

from lumen import __version__
from lumen.cli import main


def test_cli_prints_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert f"lumen {__version__}" in (result.stdout or "")
