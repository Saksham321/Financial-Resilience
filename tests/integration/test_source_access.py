import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.shared.database.models import User
from app.core.security import verify_password
from scripts.create_admin import provision_admin


@pytest.mark.asyncio
async def test_public_source_lookup_but_no_signup_or_personal_access(client, monkeypatch):
    monkeypatch.setattr(settings,'ENABLE_REGISTRATION',False)
    assert (await client.get('/api/v1/datasets/overview')).status_code == 200
    assert (await client.get('/api/v1/datasets/accounts')).status_code == 200
    assert (await client.get('/api/v1/finance/dashboard')).status_code == 401
    assert (await client.get('/api/v1/system/metrics')).status_code == 401
    response=await client.post('/api/v1/auth/register',json={
        'email':'blocked@example.com','password':'TestOnly123!','first_name':'No','last_name':'Signup'})
    assert response.status_code==403


@pytest.mark.asyncio
async def test_explicit_admin_provisioning_hashes_password_and_can_login(client,test_db_session):
    connection=await test_db_session.connection()
    def setup(sync_connection):
        with Session(bind=sync_connection) as db:
            provision_admin(db,'admin-test@example.com','TestOnlyAdmin321!')
            db.commit()
    await connection.run_sync(setup)
    user=await test_db_session.scalar(select(User).where(User.email=='admin-test@example.com'))
    assert user.role=='admin' and user.hashed_password!='TestOnlyAdmin321!'
    assert verify_password('TestOnlyAdmin321!',user.hashed_password)
    result=await client.post('/api/v1/auth/login',json={'email':'admin-test@example.com','password':'TestOnlyAdmin321!'})
    assert result.status_code==200 and result.json()['role']=='admin'
    headers={'Authorization':'Bearer '+result.json()['access_token']}
    assert (await client.get('/api/v1/system/metrics',headers=headers)).status_code==200
