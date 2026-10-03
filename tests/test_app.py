import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import app as activities_app
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials


class ActivityManagementTests(unittest.TestCase):
    def setUp(self):
        self.original_activities = copy.deepcopy(activities_app.activities)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.activities_file = Path(self.temp_dir.name) / "activities.json"
        self.teachers_file = Path(self.temp_dir.name) / "teachers.json"
        self.file_patches = [
            patch.object(activities_app, "ACTIVITIES_FILE", self.activities_file),
            patch.object(activities_app, "TEACHERS_FILE", self.teachers_file),
        ]
        for file_patch in self.file_patches:
            file_patch.start()
        activities_app.activities.clear()

    def tearDown(self):
        activities_app.activities.clear()
        activities_app.activities.update(self.original_activities)
        for file_patch in self.file_patches:
            file_patch.stop()
        self.temp_dir.cleanup()

    def test_create_update_roster_capacity_and_delete_are_persisted(self):
        activities_app.create_activity(
            activities_app.ActivityCreate(
                name="Robotics",
                description="Build robots",
                schedule="Mondays",
                max_participants=2,
                leader="teacher@school.edu",
            )
        )
        activities_app.add_roster_participant(
            "Robotics", activities_app.Participant(email="student@school.edu")
        )
        activities_app.add_roster_participant(
            "Robotics", activities_app.Participant(email="another@school.edu")
        )

        with self.assertRaises(HTTPException) as full_activity:
            activities_app.signup_for_activity("Robotics", "third@school.edu")
        self.assertEqual(full_activity.exception.status_code, 400)

        activities_app.update_activity(
            "Robotics",
            activities_app.ActivityUpdate(
                name="Robotics Club",
                schedule="Tuesdays",
                leader="student-leader@school.edu",
            ),
        )
        saved = json.loads(self.activities_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["Robotics Club"]["schedule"], "Tuesdays")
        self.assertEqual(saved["Robotics Club"]["leader"], "student-leader@school.edu")
        self.assertEqual(
            saved["Robotics Club"]["participants"],
            ["student@school.edu", "another@school.edu"],
        )

        with self.assertRaises(HTTPException) as capacity:
            activities_app.update_activity(
                "Robotics Club",
                activities_app.ActivityUpdate(max_participants=1),
            )
        self.assertEqual(capacity.exception.status_code, 400)

        activities_app.remove_roster_participant(
            "Robotics Club", "student@school.edu"
        )
        activities_app.remove_roster_participant(
            "Robotics Club", "another@school.edu"
        )
        activities_app.delete_activity("Robotics Club")
        self.assertEqual(json.loads(self.activities_file.read_text()), {})

    def test_staff_credentials_are_required(self):
        self.teachers_file.write_text(
            json.dumps({"teacher": "example"}), encoding="utf-8"
        )
        credentials = HTTPBasicCredentials(
            **{"username": "teacher", "password": "example"}
        )
        self.assertIsNone(activities_app.require_staff(credentials))

        with self.assertRaises(HTTPException) as unauthorized:
            activities_app.require_staff(
                HTTPBasicCredentials(
                    **{"username": "student", "password": "example"}
                )
            )
        self.assertEqual(unauthorized.exception.status_code, 401)

    def test_mutating_routes_require_staff_authentication(self):
        for route in activities_app.app.routes:
            if route.path.startswith("/activities") and route.methods & {
                "POST",
                "PUT",
                "DELETE",
            }:
                self.assertTrue(route.dependant.dependencies, route.path)


if __name__ == "__main__":
    unittest.main()
