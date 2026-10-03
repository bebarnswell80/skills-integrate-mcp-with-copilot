# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities`                                                     | Create an activity                                                  |
| PUT    | `/activities/{activity_name}`                                     | Update activity details, leader, or name                             |
| DELETE | `/activities/{activity_name}`                                     | Delete an activity                                                  |
| POST   | `/activities/{activity_name}/participants`                        | Add a roster member                                                 |
| DELETE | `/activities/{activity_name}/participants?email=...`              | Remove a roster member                                              |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up a student                                                   |
| DELETE | `/activities/{activity_name}/unregister?email=...`                | Unregister a student                                                |

All activity changes and roster operations require HTTP Basic authentication
for a staff account. Create a private `src/teachers.json` file from
`src/teachers.example.json`:

```sh
cp src/teachers.example.json src/teachers.json
```

The local file is ignored by Git to prevent credentials from being committed.
It maps usernames to passwords, for example:

```json
{
  "teacher": "replace-with-a-unique-password"
}
```

Use unique assigned passwords and serve the API over HTTPS. Add staff
credentials before using the management endpoints. Activities are stored in
`src/activities.json`, so changes survive a restart and are reflected by the
public `GET /activities` endpoint.

Creating an activity requires `name`, `description`, `schedule`, and
`max_participants`; `leader` is optional. Updates accept any of those fields.
Capacity cannot be reduced below the current roster size, and signing up a
student fails when the activity is full.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity details and participant rosters are persisted in `src/activities.json`.
