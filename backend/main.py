import os
from fastapi import FastAPI
from database import Base, engine
from controllers.auth_controller import auth_controller
from controllers.verification_controller import verification_controller
from controllers.admin_controller import admin_controller
from controllers.profile_controller import profile_controller
from controllers.interest_controller import interest_controller
from controllers.notification_controller import notification_controller
from controllers.message_controller import message_controller
from controllers import trust_safety_controller
from models.message.message import Message
from models.block import Block
from models.report import Report
from models.verification_rejection import VerificationRejection
from create_db import create_database
from middlewares import cors_middleware
from middlewares import static_middleware

app = FastAPI()

if not os.getenv("ENV"):
    os.environ["ENV"] = "dev"

cors_middleware.add(app)
static_middleware.add(app)

create_database()
# Initialize the database
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(auth_controller.router, prefix="/auth", tags=["auth"])
app.include_router(verification_controller.router, prefix="/verification", tags=["verification"])
app.include_router(admin_controller.router, prefix="/admin", tags=["admin"])
app.include_router(profile_controller.router, prefix="/api", tags=["profile"])
app.include_router(interest_controller.router, prefix="/api", tags=["interests"])
app.include_router(notification_controller.router, prefix="/api", tags=["notifications"])
app.include_router(message_controller.router, prefix="/api", tags=["messages"])
app.include_router(trust_safety_controller.router, prefix="/api", tags=["trust-safety"])
