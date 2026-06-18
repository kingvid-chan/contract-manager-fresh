"""User service — business logic for user management."""

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.auth import hash_password


def get_user_by_username(db: Session, username: str) -> User | None:
    """Fetch a user by username (case-insensitive is not required per spec)."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Fetch a user by primary key."""
    return db.query(User).get(user_id)


def list_users(db: Session) -> list[User]:
    """Return all users ordered by id."""
    return db.query(User).order_by(User.id).all()


def create_user(db: Session, username: str, password: str, role: str = "user") -> User:
    """Create a new user with hashed password."""
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, **kwargs) -> User:
    """Update user fields. If 'password' is in kwargs, hash it as password_hash."""
    if "password" in kwargs:
        kwargs["password_hash"] = hash_password(kwargs.pop("password"))
    for key, value in kwargs.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    """Delete a user. Callers must guard against self-deletion."""
    db.delete(user)
    db.commit()


def toggle_user_status(db: Session, user: User) -> User:
    """Flip user status between active and disabled."""
    user.status = "disabled" if user.status == "active" else "active"
    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, user: User, new_password: str) -> User:
    """Reset a user's password to a new value."""
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user
