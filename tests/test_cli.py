import sys
from unittest.mock import patch
import pytest
from learnkit.cli import main
from learnkit.core import LearnKit

def test_cli_maintain_help(capsys):
    with patch.object(sys, "argv", ["learnkit", "--help"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "LearnKit Command Line Interface" in captured.out

def test_cli_maintain_run(tmp_path, capsys):
    db_file = tmp_path / "test_mem.db"
    # Seed a simple db using LearnKit
    lk = LearnKit(memory_backend="sqlite", db_path=str(db_file))
    lk.shutdown()

    # Call CLI to maintain
    with patch.object(sys, "argv", ["learnkit", "maintain", "--db-path", str(db_file), "--weeks", "1", "--decay-rate", "0.05"]):
        main()
        
    captured = capsys.readouterr()
    assert "Running maintenance on database" in captured.out
    assert "Maintenance completed successfully" in captured.out
    assert "Decayed records:" in captured.out
