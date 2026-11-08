"""Exercise actual Alembic revisions against an isolated disk database."""
import os
import subprocess
import sys
import sqlite3


def test_upgrade_downgrade_roundtrip(tmp_path):
    path=tmp_path/'migration.db'
    env={**os.environ,'DATABASE_URL':'sqlite+aiosqlite:///'+path.as_posix(),'DEBUG':'false','USE_LOCAL_FALLBACK_DB':'false'}
    def migrate(target):
        result=subprocess.run([sys.executable,'-m','alembic',*target],env=env,text=True,capture_output=True,timeout=60)
        assert result.returncode==0,result.stdout+result.stderr
    migrate(['upgrade','head'])
    with sqlite3.connect(path) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'ledger_transactions','installment_offers','vacations','cpi_observations','users','notifications'}<=tables
        indexes={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        assert any('ledger_transactions' in name for name in indexes)
        assert list(db.execute('PRAGMA foreign_key_list(bank_accounts)'))
    migrate(['downgrade','95c6cf829e7c'])
    with sqlite3.connect(path) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'users' in tables and 'ledger_transactions' not in tables
    migrate(['upgrade','head'])


def test_adopt_legacy_metadata_database_without_losing_records(tmp_path):
    path=tmp_path/'legacy.db'
    env={**os.environ,'DATABASE_URL':'sqlite+aiosqlite:///'+path.as_posix(),'DEBUG':'false','USE_LOCAL_FALLBACK_DB':'false'}
    setup=subprocess.run([sys.executable,'-c','from app.shared.database.session import sync_engine; from app.shared.database.models import Base; Base.metadata.create_all(sync_engine)'],env=env,text=True,capture_output=True,timeout=30)
    assert setup.returncode==0,setup.stderr
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO users (id,email,hashed_password,is_active,is_verified,role,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000001','legacy@example.com','not-a-real-password-hash',1,0,'user','2026-01-01','2026-01-01')")
    result=subprocess.run([sys.executable,'-m','scripts.migrate'],env=env,text=True,capture_output=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0]==1
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='core_integrity_v1'
