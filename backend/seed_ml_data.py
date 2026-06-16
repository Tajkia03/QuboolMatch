# backend/seed_ml_data.py

import pandas as pd
import uuid
import bcrypt
import random
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, text


DB_URL = "postgresql://postgres:mim123@localhost:5432/qubool"
LIMIT = 30000            # how many demo users to create
BATCH_SIZE = 300      # commit per batch (safe on memory)
DEFAULT_PASSWORD = "seed123"


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "ml_artifacts" / "clean_profiles.csv"

engine = create_engine(DB_URL, pool_pre_ping=True)




def hash_password_demo(pw: str) -> str:
    """
    Hash password using bcrypt to match the application's authentication system.
    """
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode()


def safe_str(x, limit=255):
    if x is None:
        return None
    s = str(x)
    if s.lower() == "nan":
        return None
    return s[:limit]


def map_gender(sex):
    s = str(sex).lower().strip()
    if s in ["m", "male"]:
        return "male"
    if s in ["f", "female"]:
        return "female"
    return "other"


def map_diet(d):
    d = str(d).lower().strip()
    if d == "nan" or d == "" or d == "none":
        return None
    if "vegan" in d:
        return "vegan"
    if "vegetarian" in d:
        return "vegetarian"
    # keep as "non-vegetarian" or simply store original if you prefer
    return "non-vegetarian"


def map_smoking(v):
    v = str(v).lower().strip()
    if v == "nan" or v == "" or v == "none":
        return None
    if "no" in v or "never" in v:
        return "no"
    if "yes" in v:
        return "yes"
    # sometimes / trying to quit / socially -> keep "sometimes"
    return "sometimes"


def map_alcohol(v):
    v = str(v).lower().strip()
    if v == "nan" or v == "" or v == "none":
        return None
    if "not at all" in v or "never" in v:
        return "no"
    # socially/often/very often -> yes
    return "yes"


def map_religion(r):
    # Keep a short version; you can normalize later if needed
    rr = safe_str(r, 120)
    if rr is None:
        return None
    return rr


def generate_height_weight(gender, age):
    """Generate realistic height and weight based on gender and age"""
    if gender == "male":
        height = random.uniform(165, 185)  # cm
        weight = random.uniform(60, 90)    # kg
    elif gender == "female":
        height = random.uniform(152, 172)  # cm
        weight = random.uniform(45, 75)    # kg
    else:
        height = random.uniform(160, 180)
        weight = random.uniform(55, 85)
    
    return round(height, 1), round(weight, 1)


def generate_blood_group():
    """Generate random blood group"""
    blood_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    return random.choice(blood_groups)


def generate_health_status():
    """Generate overall health status"""
    statuses = ["Excellent", "Good", "Fair"]
    weights = [0.4, 0.5, 0.1]  # Most people report good to excellent health
    return random.choices(statuses, weights=weights)[0]


def generate_partner_preferences(user_age, user_gender, user_religion, user_height):
    """Generate realistic partner preferences based on user's attributes"""
    prefs = {}
    
    # Age preferences (typically ±5 years)
    prefs["preferred_age_min"] = max(18, user_age - 5)
    prefs["preferred_age_max"] = min(60, user_age + 5)
    
    # Height preferences
    if user_gender == "male":
        # Males typically prefer similar or shorter height
        prefs["preferred_height_min"] = 150.0
        prefs["preferred_height_max"] = user_height
    elif user_gender == "female":
        # Females typically prefer similar or taller height
        prefs["preferred_height_min"] = user_height - 5
        prefs["preferred_height_max"] = 190.0
    else:
        prefs["preferred_height_min"] = 155.0
        prefs["preferred_height_max"] = 185.0
    
    # Weight preferences (healthy range)
    prefs["preferred_weight_min"] = 45.0
    prefs["preferred_weight_max"] = 90.0
    
    # Religion preference (usually same religion)
    prefs["preferred_religion"] = user_religion
    
    # Willing to relocate
    prefs["willing_to_relocate"] = random.choice([True, False])
    
    # Living with in-laws preference
    prefs["living_with_in_laws"] = random.choice(["yes", "no", "open to discussion"])
    
    return prefs


def generate_interests(hobbies):
    """Extract or generate interests from hobbies text"""
    common_interests = [
        "Reading", "Travel", "Cooking", "Movies", "Music", 
        "Sports", "Photography", "Fitness", "Art", "Technology",
        "Nature", "Writing", "Gaming", "Dancing", "Volunteering"
    ]
    # Pick 3-5 random interests
    num_interests = random.randint(3, 5)
    return ", ".join(random.sample(common_interests, num_interests))


# -------------------------
# Core insert batch
# -------------------------
def insert_batch(users_batch, profiles_batch):
    """
    Inserts into users, then inserts into profiles using user_id.
    Uses a transaction; if anything fails, this batch rolls back.
    """
    with engine.begin() as conn:
        # 1) Insert USERS (only columns that exist in your users table)
        conn.execute(
            text("""
                INSERT INTO users
                (id, name, email, hashed_password, gender, nid, age, religion, is_demo, is_admin, is_deleted, created_at, verification_status)
                VALUES
                (:id, :name, :email, :hashed_password, :gender, :nid, :age, :religion, :is_demo, :is_admin, :is_deleted, :created_at, :verification_status)
                ON CONFLICT (email) DO NOTHING
            """),
            users_batch
        )

        # 2) Insert PROFILES (user_id already set in profiles_batch)
        conn.execute(
            text("""
                INSERT INTO profiles
                (id, user_id, location, academic_background, profession, marital_status, hobbies,
                 height, weight, blood_group, overall_health_status, long_term_condition, 
                 disability, chronic_illness, fertility_awareness,
                 dietary_preference, smoking_habit, alcohol_consumption, interests,
                 preferred_age_min, preferred_age_max, preferred_height_min, preferred_height_max,
                 preferred_weight_min, preferred_weight_max, preferred_religion, preferred_education,
                 preferred_profession, preferred_location, willing_to_relocate,
                 lifestyle_pref_smoking, lifestyle_pref_alcohol, lifestyle_pref_dietary_match,
                 living_with_in_laws, career_support_expectations, additional_comments,
                 is_completed, is_demo, created_at, updated_at)
                VALUES
                (:id, :user_id, :location, :academic_background, :profession, :marital_status, :hobbies,
                 :height, :weight, :blood_group, :overall_health_status, :long_term_condition,
                 :disability, :chronic_illness, :fertility_awareness,
                 :dietary_preference, :smoking_habit, :alcohol_consumption, :interests,
                 :preferred_age_min, :preferred_age_max, :preferred_height_min, :preferred_height_max,
                 :preferred_weight_min, :preferred_weight_max, :preferred_religion, :preferred_education,
                 :preferred_profession, :preferred_location, :willing_to_relocate,
                 :lifestyle_pref_smoking, :lifestyle_pref_alcohol, :lifestyle_pref_dietary_match,
                 :living_with_in_laws, :career_support_expectations, :additional_comments,
                 :is_completed, :is_demo, :created_at, :updated_at)
            """),
            profiles_batch
        )

    print(f"✅ Inserted batch: {len(users_batch)} users + profiles")


def seed(limit=LIMIT):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found at: {CSV_PATH}")

    # read csv safely
    df = pd.read_csv(CSV_PATH, engine="python", on_bad_lines="skip")

    # choose sample
    df = df.sample(n=min(limit, len(df)), random_state=42).reset_index(drop=True)

    pw_hash = hash_password_demo(DEFAULT_PASSWORD)

    users_batch = []
    profiles_batch = []

    for i, r in df.iterrows():
        print(f"Processing row {i + 1}/{len(df)}", end="\r")
        uid = uuid.uuid4().hex[:10]
        user_id = str(uuid.uuid4())  # Generate UUID for user
        email = f"seed_{uid}@demo.quboolmatch.com"
        nid = f"SEED_{uuid.uuid4().hex[:12]}"

        age = int(r["age"]) if pd.notna(r.get("age")) else None
        gender = map_gender(r.get("sex"))
        religion = map_religion(r.get("religion"))
        
        # Generate physical attributes
        height, weight = generate_height_weight(gender, age if age else 25)

        # ---- USERS payload (matches your users columns) ----
        users_batch.append({
            "id": user_id,
            "name": f"DemoUser{uid}",
            "email": email,
            "hashed_password": pw_hash,
            "gender": gender,
            "nid": nid,
            "age": age,
            "religion": religion,
            "is_demo": True,
            "is_admin": False,
            "is_deleted": False,
            "created_at": datetime.now(timezone.utc),
            "verification_status": "verified"  # Mark demo users as verified
        })
        
        # Generate partner preferences
        partner_prefs = generate_partner_preferences(
            age if age else 25, 
            gender, 
            religion,
            height
        )

        # ---- PROFILES payload (matches your profiles columns) ----
        profiles_batch.append({
            "id": str(uuid.uuid4()),  # Generate UUID for profile
            "user_id": user_id,  # Use the generated user_id
            "location": safe_str(r.get("location"), 200),
            "academic_background": safe_str(r.get("education"), 200),
            "profession": safe_str(r.get("job"), 200),
            "marital_status": "single",
            "hobbies": safe_str(r.get("essay_text", ""), 2000),
            
            # Physical attributes
            "height": height,
            "weight": weight,
            
            # Health information
            "blood_group": generate_blood_group(),
            "overall_health_status": generate_health_status(),
            "long_term_condition": "no",
            "disability": "no",
            "chronic_illness": "none",
            "fertility_awareness": random.choice(["yes", "no", "not sure"]),
            
            # Lifestyle habits
            "dietary_preference": map_diet(r.get("diet")),
            "smoking_habit": map_smoking(r.get("smokes")),
            "alcohol_consumption": map_alcohol(r.get("drinks")),
            "interests": generate_interests(safe_str(r.get("essay_text", ""))),
            
            # Partner preferences
            "preferred_age_min": partner_prefs["preferred_age_min"],
            "preferred_age_max": partner_prefs["preferred_age_max"],
            "preferred_height_min": partner_prefs["preferred_height_min"],
            "preferred_height_max": partner_prefs["preferred_height_max"],
            "preferred_weight_min": partner_prefs["preferred_weight_min"],
            "preferred_weight_max": partner_prefs["preferred_weight_max"],
            "preferred_religion": partner_prefs["preferred_religion"],
            "preferred_education": safe_str(r.get("education"), 200),
            "preferred_profession": random.choice(["Any", "Professional", "Business", "Government Service"]),
            "preferred_location": safe_str(r.get("location"), 200),
            "willing_to_relocate": partner_prefs["willing_to_relocate"],
            
            # Lifestyle preferences for partner
            "lifestyle_pref_smoking": random.choice(["no", "doesn't matter"]),
            "lifestyle_pref_alcohol": random.choice(["no", "doesn't matter"]),
            "lifestyle_pref_dietary_match": random.choice([True, False]),
            
            # Marriage preferences
            "living_with_in_laws": partner_prefs["living_with_in_laws"],
            "career_support_expectations": random.choice([
                "Supportive of my career goals",
                "Open to discussion",
                "Traditional family roles preferred"
            ]),
            "additional_comments": "Looking for a genuine connection and lifelong partnership.",
            
            # System fields
            "is_completed": True,   # important so these are eligible for matching
            "is_demo": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
        
        # batch commit
        if (i + 1) % BATCH_SIZE == 0:
            insert_batch(users_batch, profiles_batch)
            users_batch, profiles_batch = [], []

    # last batch
    if users_batch:
        insert_batch(users_batch, profiles_batch)

    print("\n✅ Seeding complete.")
    print(f"🔑 Demo password for all seeded users: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    seed(LIMIT)
