from models.user.user import User
from models.email_verification_code import EmailVerificationCode

def test_sign_up_success(client, db_session, monkeypatch):
    monkeypatch.setattr("services.email_verification_service._generate_pin", lambda: "123456")
    payload = {
        "name": "New User",
        "email": "newuser@example.com", 
        "password": "Aa1!aaa",
        "gender": "Male",
        "nid": "NID_12345",
        "age": 25,
        "religion": "Islam",
        "preferred_age_from": 20,
        "preferred_age_to": 30
    }
    
    response = client.post("/auth/sign_up", json=payload)
    assert response.status_code == 201  # Status code 201 for successful creation
    
    data = response.json()
    assert data["email_verification_required"] is True
    assert data["email"] == "newuser@example.com"
    assert "user_id" in data
    assert "access_token" not in data
    assert db_session.query(EmailVerificationCode).filter_by(user_id=data["user_id"]).count() == 1


def test_verify_email_success_returns_token(client, monkeypatch):
    monkeypatch.setattr("services.email_verification_service._generate_pin", lambda: "123456")
    payload = {
        "name": "Verify User",
        "email": "verifyuser@example.com",
        "password": "Aa1!aaa",
        "gender": "Male",
        "nid": "NID_VERIFY_EMAIL",
        "age": 25,
        "preferred_age_from": 20,
        "preferred_age_to": 30
    }

    signup_response = client.post("/auth/sign_up", json=payload)
    assert signup_response.status_code == 201
    signup_data = signup_response.json()

    response = client.post("/auth/verify-email", json={
        "user_id": signup_data["user_id"],
        "email": signup_data["email"],
        "pin": "123456",
    })

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


# Test sign_up failure (email already exists)
def test_sign_up_user_exists(client, db_session):
    payload = {
        "name": "Test User 1",
        "email": "testuser1@example.com", 
        "password": "Password123!",
        "gender": "Female",
        "nid": "NID_54321",
        "age": 24,
        "preferred_age_from": 20,
        "preferred_age_to": 30
    }

    user = User(
        name="Existing User",
        email="testuser1@example.com", 
        password="Password123!",
        gender="Male",
        nid="NID_EXISTING",
        age=30
    )
    db_session.add(user)
    db_session.commit()

    response = client.post("/auth/sign_up", json=payload)
    assert response.status_code == 400
    assert response.json() == {'detail': 'User already registered or NID already exists'}


def test_sign_up_rejects_weak_password(client):
    payload = {
        "name": "Weak Password User",
        "email": "weakpassword@example.com",
        "password": "123123",
        "gender": "Male",
        "nid": "NID_WEAK_PASSWORD",
        "age": 25,
        "preferred_age_from": 20,
        "preferred_age_to": 30
    }

    response = client.post("/auth/sign_up", json=payload)
    assert response.status_code == 422
    response_json = response.json()
    assert "uppercase, lowercase, number, and special character" in str(response_json["detail"])


def test_sign_up_rejects_missing_required_signup_fields(client):
    payload = {
        "name": "Missing Fields User",
        "email": "missingfields@example.com",
        "password": "Aa1!aaa",
        "gender": "Male",
        "nid": "NID_MISSING_FIELDS",
        "age": 25
    }

    response = client.post("/auth/sign_up", json=payload)
    assert response.status_code == 422
    response_json = response.json()
    assert "preferred_age_from" in str(response_json["detail"])
    assert "preferred_age_to" in str(response_json["detail"])


# Test sign_in success
def test_sign_in_success(client, db_session):
    user_payload = {"email": "testuser2@example.com", "password": "Password123!"}
    user = User(
        name="Test User 2",
        email="testuser2@example.com", 
        password="Password123!",
        gender="Male",
        nid="NID_TEST2",
        age=28
    )
    user.email_verified = True
    db_session.add(user)
    db_session.commit()

    response = client.post("/auth/sign_in", json=user_payload)
    assert response.status_code == 200
    response_json = response.json()
    assert "access_token" in response_json
    assert response_json["access_token"] != ""


# Test sign_in failure (incorrect password)
def test_sign_in_incorrect_password(client, db_session):
    user_payload = {"email": "testuser3@example.com", "password": "WrongPassword"}
    user = User(
        name="Test User 3",
        email="testuser3@example.com", 
        password="123123",
        gender="Female",
        nid="NID_TEST3",
        age=26
    )
    user.email_verified = True
    db_session.add(user)
    db_session.commit()

    response = client.post("/auth/sign_in", json=user_payload)
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


# Test sign_in failure (user not found)
def test_sign_in_user_not_found(client):
    user_payload = {"email": "nonexistentuser@example.com", "password": "Password123!"}

    response = client.post("/auth/sign_in", json=user_payload)
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}
