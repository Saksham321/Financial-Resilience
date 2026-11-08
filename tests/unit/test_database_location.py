from pathlib import Path
from sqlalchemy.engine import make_url
from app.core.config import PROJECT_ROOT,Settings
from app.shared.database import session


def test_ide_working_directory_does_not_select_a_different_database(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(session.settings,'DATABASE_URL','sqlite+aiosqlite:///./financial_resilience.db')
    async_url,sync_url=session._resolve_database_urls()
    expected=str((PROJECT_ROOT/'financial_resilience.db').resolve())
    assert make_url(async_url).database==expected
    assert make_url(sync_url).database==expected
    assert not (tmp_path/'financial_resilience.db').exists()
    assert Settings.model_config['env_file']==PROJECT_ROOT/'.env'


def test_explicit_database_and_memory_targets_are_preserved(tmp_path,monkeypatch):
    path=(tmp_path/'isolated.db').resolve()
    monkeypatch.setattr(session.settings,'DATABASE_URL','sqlite:///'+path.as_posix())
    assert Path(make_url(session._resolve_database_urls()[0]).database)==path
    monkeypatch.setattr(session.settings,'DATABASE_URL','sqlite:///:memory:')
    assert make_url(session._resolve_database_urls()[0]).database==':memory:'
