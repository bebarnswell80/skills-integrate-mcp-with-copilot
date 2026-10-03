"""
High School Management System API

A FastAPI application for viewing and managing extracurricular activities.
"""

import json
import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and managing extracurricular activities",
)

current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

ACTIVITIES_FILE = current_dir / "activities.json"
TEACHERS_FILE = current_dir / "teachers.json"
security = HTTPBasic()


def load_activities():
    with ACTIVITIES_FILE.open(encoding="utf-8") as activities_file:
        return json.load(activities_file)


def save_activities():
    temporary_file = ACTIVITIES_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(activities, indent=2) + "\n", encoding="utf-8"
    )
    temporary_file.replace(ACTIVITIES_FILE)


activities = load_activities()


class ActivityCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str
    schedule: str
    max_participants: int = Field(gt=0)
    leader: Optional[str] = None


class ActivityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    schedule: Optional[str] = None
    max_participants: Optional[int] = Field(default=None, gt=0)
    leader: Optional[str] = None


class Participant(BaseModel):
    email: str = Field(min_length=1)


def require_staff(credentials: HTTPBasicCredentials = Depends(security)):
    try:
        with TEACHERS_FILE.open(encoding="utf-8") as teachers_file:
            teachers = json.load(teachers_file)
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Staff credentials are unavailable")
    if not isinstance(teachers, dict):
        raise HTTPException(status_code=503, detail="Staff credentials are unavailable")

    authenticated = False
    for username, password in teachers.items():
        if not isinstance(username, str) or not isinstance(password, str):
            raise HTTPException(
                status_code=503, detail="Staff credentials are unavailable"
            )
        username_matches = secrets.compare_digest(
            username.encode("utf-8"), credentials.username.encode("utf-8")
        )
        password_matches = secrets.compare_digest(
            password.encode("utf-8"), credentials.password.encode("utf-8")
        )
        authenticated = authenticated or (username_matches and password_matches)

    if not authenticated:
        raise HTTPException(
            status_code=401,
            detail="Invalid staff credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def get_activity(activity_name: str):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activities[activity_name]


def add_participant(activity_name: str, email: str):
    activity = get_activity(activity_name)
    if email in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is already signed up")
    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is full")
    activity["participants"].append(email)
    save_activities()
    return {"message": f"Signed up {email} for {activity_name}"}


def remove_participant(activity_name: str, email: str):
    activity = get_activity(activity_name)
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity",
        )
    activity["participants"].remove(email)
    save_activities()
    return {"message": f"Unregistered {email} from {activity_name}"}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities", status_code=201, dependencies=[Depends(require_staff)])
def create_activity(activity_details: ActivityCreate):
    if activity_details.name in activities:
        raise HTTPException(status_code=409, detail="Activity already exists")
    activities[activity_details.name] = {
        "description": activity_details.description,
        "schedule": activity_details.schedule,
        "max_participants": activity_details.max_participants,
        "participants": [],
        "leader": activity_details.leader,
    }
    save_activities()
    return {"message": f"Created {activity_details.name}"}


@app.put(
    "/activities/{activity_name}",
    dependencies=[Depends(require_staff)],
)
def update_activity(activity_name: str, updates: ActivityUpdate):
    activity = get_activity(activity_name)
    if hasattr(updates, "model_dump"):
        updated_fields = updates.model_dump(exclude_unset=True)
    else:
        updated_fields = updates.dict(exclude_unset=True)
    new_name = updated_fields.pop("name", activity_name)

    if new_name is None or any(
        updated_fields.get(field) is None
        for field in ("description", "schedule", "max_participants")
        if field in updated_fields
    ):
        raise HTTPException(status_code=422, detail="Activity details cannot be null")

    if new_name != activity_name and new_name in activities:
        raise HTTPException(status_code=409, detail="Activity already exists")

    if (
        "max_participants" in updated_fields
        and updated_fields["max_participants"] < len(activity["participants"])
    ):
        raise HTTPException(
            status_code=400,
            detail="Capacity cannot be lower than the current roster",
        )

    activity.update(updated_fields)
    if new_name != activity_name:
        activities[new_name] = activities.pop(activity_name)
    save_activities()
    return {"message": f"Updated {new_name}"}


@app.delete(
    "/activities/{activity_name}",
    dependencies=[Depends(require_staff)],
)
def delete_activity(activity_name: str):
    get_activity(activity_name)
    del activities[activity_name]
    save_activities()
    return {"message": f"Deleted {activity_name}"}


@app.post(
    "/activities/{activity_name}/participants",
    status_code=201,
    dependencies=[Depends(require_staff)],
)
def add_roster_participant(activity_name: str, participant: Participant):
    return add_participant(activity_name, participant.email)


@app.delete(
    "/activities/{activity_name}/participants",
    dependencies=[Depends(require_staff)],
)
def remove_roster_participant(activity_name: str, email: str):
    return remove_participant(activity_name, email)


@app.post("/activities/{activity_name}/signup", dependencies=[Depends(require_staff)])
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity."""
    return add_participant(activity_name, email)


@app.delete(
    "/activities/{activity_name}/unregister",
    dependencies=[Depends(require_staff)],
)
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity."""
    return remove_participant(activity_name, email)
