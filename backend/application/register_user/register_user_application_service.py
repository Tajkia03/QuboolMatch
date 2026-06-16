from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.user.user import User
from shared.transaction_manager import TransactionManager
from typing import Optional


class UserRegistrationData(BaseModel):
    name: str
    email: str
    password: str
    gender: str
    nid: str
    age: int
    religion: Optional[str] = None
    preferred_age_from: Optional[int] = None
    preferred_age_to: Optional[int] = None


def execute(params: UserRegistrationData, db: Session):
    """
    Creates a new user in the database with a transaction.
    """
    transaction_manager = TransactionManager(db)

    # Server-side validations
    if params.age < 18:
        raise ValueError('User must be at least 18 years old to register')

    pf = params.preferred_age_from
    pt = params.preferred_age_to

    if pf is not None and pf < 18:
        raise ValueError("Preferred age range 'From' must be at least 18")
    if pt is not None and pt < 18:
        raise ValueError("Preferred age range 'To' must be at least 18")

    # Reject if preferred range 'from' is greater than 'to'
    if pf is not None and pt is not None and pf > pt:
        raise ValueError("Preferred age range 'From' must be less than or equal to 'To'")

    try:
        with transaction_manager.transaction() as session:
            # Create a new user object and add it to the session
            new_user = User(
                name=params.name,
                email=params.email,
                password=params.password,
                gender=params.gender,
                nid=params.nid,
                age=params.age,
                religion=params.religion,
                preferred_age_from=pf,
                preferred_age_to=pt
            )
            session.add(new_user)

    except IntegrityError as e:
            raise ValueError('User already registered or NID already exists') from e

    return new_user
