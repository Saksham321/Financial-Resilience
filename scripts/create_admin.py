"""Provision an administrator explicitly; passwords are never stored as plaintext."""
import argparse
import getpass
import sys
from sqlalchemy import select
from app.core.security import hash_password
from app.shared.schemas.auth import LoginRequest
from app.shared.database.models import User, UserProfile, UserPreference, AuditLog


def provision_admin(db, email, password):
    credentials = LoginRequest(email=email, password=password)
    user = db.scalar(select(User).where(User.email == credentials.email))
    created = user is None
    if created:
        user = User(email=credentials.email)
        db.add(user)
    user.hashed_password = hash_password(credentials.password)
    user.role = 'admin'
    user.is_active = True
    user.is_verified = True
    db.flush()
    if db.scalar(select(UserProfile).where(UserProfile.user_id == user.id)) is None:
        db.add(UserProfile(user_id=user.id, first_name='Tangerine', last_name='Administrator', province='Ontario'))
    if db.scalar(select(UserPreference).where(UserPreference.user_id == user.id)) is None:
        db.add(UserPreference(user_id=user.id, consent_ai_processing=False, consent_browsing_context=False))
    db.add(AuditLog(user_id=user.id,event_type='ADMIN_PROVISIONED',details={'created':created}))
    return user


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email',required=True)
    args=parser.parse_args()
    password=getpass.getpass('Admin password: ') if sys.stdin.isatty() else sys.stdin.readline().rstrip('\r\n')
    from app.shared.database.session import SyncSessionLocal
    with SyncSessionLocal() as db:
        user=provision_admin(db,args.email,password)
        db.commit()
        print('Administrator provisioned:',user.email)


if __name__=='__main__':
    main()
