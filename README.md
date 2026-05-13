# Online Assignment Submission Management System (OASMS)

## Project Overview
OASMS is a Flask-based web application designed to streamline assignment distribution, file submission, grading, and administrative reporting for educational programs. It supports role-based access for students, instructors, and administrators.

## Goals
- Provide students with a simple way to view assignments and upload submissions.
- Give instructors tools to review work, grade submissions, and leave comments.
- Offer admins analytics and data integrity checks for users, courses, and assignments.
- Reduce manual tracking and improve transparency across assignment workflows.

## Target Audience
- Students who need a central place to submit assignments.
- Instructors who need to manage grading and submission review.
- Administrators who oversee user accounts, course assignment ownership, and reporting.
- Academic coordinators who need visibility into assignment status and grading performance.

## Required Pages
- Home / Landing Page
- Login Page
- Register Page
- Student Dashboard
- Assignment List / Details Page
- Upload Submission Page
- Instructor Dashboard
- Grade Student Page
- View Submissions Page
- Admin Dashboard
- Manage Students Page
- Manage Courses / Assignments Page
- Report / Analytics Page
- Error / Access Denied Page

## Core Features
- User authentication and role-based access control
- Assignment listing and assignment detail views
- Student submission upload workflow
- Instructor grading workflow with score/comments
- Admin dashboard with user, assignment, and instructor metrics
- Submission status and grade visibility for students
- Inline file preview / download links
- Course association for assignments and instructor ownership tracking
- Admin alerts for assignments missing instructor linkage

## Feature Priorities
- Must-have: authentication, assignment listing, upload submission, grading workflow, admin reporting, submission status visibility
- Should-have: inline file preview, ownership tracking, integrity alerts
- Nice-to-have: reviewer comments, notifications, exportable reports, audit logs

## User Journeys
### Student Journey
1. Login to the application
2. View assigned courses and assignments
3. Open assignment details
4. Upload a submission file
5. Confirm the upload succeeded
6. Check grade and feedback later

### Instructor Journey
1. Login to the application
2. View course assignments
3. Open an assignment to see submissions
4. Review student files
5. Assign grades and add comments
6. View grading history for students

### Admin Journey
1. Login to the application
2. Access the admin dashboard
3. Review user counts and metrics
4. Inspect instructor assignment ownership
5. Identify assignments missing instructor links
6. Manage users, courses, and assignments

## Success Metrics
- Student submission completion rate
- Speed from assignment posting to student submission
- Instructor grading turnaround time
- Number of assignments missing instructor linkage
- Admin dashboard usage
- Reduction in manual grade tracking effort

## Tech Stack
- Python 3.x
- Flask
- MySQL / MariaDB
- `mysql-connector-python`
- `bcrypt` for password hashing
- `gunicorn` for production deployment

## Repository Structure
- `frontend/app.py` — main Flask application
- `frontend/templates/` — HTML templates
- `frontend/static/css/styles.css` — stylesheet
- `frontend/uploads/` — upload storage directory
- `requirements.txt` — package dependencies
- `Procfile` — production startup command

## Setup Instructions
1. Clone the repository.
2. Create a Python virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Prepare your MySQL database and create a database named `assignment_db` (or set `DB_NAME`).
5. Set environment variables as needed:
   - `DB_HOST` (default: `localhost`)
   - `DB_PORT` (default: `3306`)
   - `DB_USER` (default: `root`)
   - `DB_PASSWORD` (default: `root`)
   - `DB_NAME` (default: `assignment_db`)
   - `SECRET_KEY` (recommended for production)
   - `UPLOAD_FOLDER` (optional; defaults to `frontend/uploads`)
6. Ensure the `frontend/uploads` directory exists and is writable.
7. Run the app locally:
   ```bash
   cd frontend
   python app.py
   ```

## Deployment
- Deploy with `gunicorn` using the Procfile:
  ```bash
  gunicorn frontend.app:app
  ```

## Notes
- The application uses a MySQL database connection in `frontend/app.py` and initializes missing schema columns at startup.
- The admin dashboard includes a check for assignments without `instructor_id`, helping catch ownership and data integrity issues.

## Contribution Guidelines
- Review existing Flask routes before adding new pages.
- Keep role-based logic consistent and secure.
- Validate file uploads and database writes.
- Test instructor and admin flows for metrics and grading functionality.

## Contact
For support or feature requests, refer to the project owner or repository maintainer.
