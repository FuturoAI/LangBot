import shutil
import sqlite3
import subprocess
from pathlib import Path


def _create_bootstrap_fixture(tmp_path: Path, source_script: Path, config_port: int) -> Path:
    repo_root = tmp_path / "repo"
    script_dir = repo_root / "scripts"
    data_dir = repo_root / "data"

    script_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    target_script = script_dir / "kuku-bootstrap.sh"
    shutil.copy2(source_script, target_script)
    target_script.chmod(0o755)

    (data_dir / "config.yaml").write_text(
        "\n".join(
            [
                "api:",
                f"    port: {config_port}",
                "    webhook_prefix: http://127.0.0.1:5300",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    db_path = data_dir / "langbot.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE api_keys (name TEXT, key TEXT, description TEXT)")
    conn.execute("CREATE TABLE bots (uuid TEXT, adapter TEXT)")
    conn.execute(
        "INSERT INTO bots (uuid, adapter) VALUES (?, ?)",
        ("bot-uuid-123", "discord"),
    )
    conn.commit()
    conn.close()

    return repo_root


def test_bootstrap_uses_configured_api_port_when_env_override_missing(tmp_path: Path):
    source_script = Path(__file__).resolve().parents[3] / "scripts" / "kuku-bootstrap.sh"
    repo_root = _create_bootstrap_fixture(tmp_path, source_script, config_port=15300)

    completed = subprocess.run(
        [str(repo_root / "scripts" / "kuku-bootstrap.sh")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "API 127.0.0.1:15300" in completed.stdout
    assert "http://127.0.0.1:15300" in (repo_root / "web" / ".env").read_text(encoding="utf-8")
    assert "http://127.0.0.1:15300" in (repo_root / ".kuku-demo.env").read_text(encoding="utf-8")
