"""
main.py
-------------------------------------------------
Run with:  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
-------------------------------------------------
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, Customer, MedicalStore
from schemas import LoginRequest, LoginResponse
from auth import create_access_token

app = FastAPI(title="Online Medical Store API")


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Single login endpoint for BOTH Customer and Store.
    Flutter sends which role the user picked (role field),
    we verify email+password+role match a row in [user],
    then pull the display name from the matching child table.
    """

    # Step 1 — find the user by email + role
    user = (
        db.query(User)
        .filter(User.email == payload.email, User.Role == payload.role)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or this account is not registered as " + payload.role,
        )

    # Step 2 — check password
    # NOTE: passwords are plain text in your current seed data ('1234').
    # For production, hash passwords (e.g. passlib/bcrypt) and compare hashes instead.
    if user.password != payload.password:
        raise HTTPException(status_code=401, detail="Incorrect password")

    # Step 3 — get display name depending on role
    name = None
    if payload.role == "Customer":
        customer = db.query(Customer).filter(Customer.c_id == user.Id).first()
        name = customer.name if customer else None
    elif payload.role == "Store":
        store = db.query(MedicalStore).filter(MedicalStore.store_id == user.Id).first()
        name = store.name if store else None
    else:
        raise HTTPException(status_code=400, detail="role must be 'Customer' or 'Store'")

    # Step 4 — issue JWT token
    token = create_access_token({"user_id": user.Id, "role": user.Role})

    return LoginResponse(
        success=True,
        message="Login successful",
        user_id=user.Id,
        role=user.Role,
        name=name,
        token=token,
    )