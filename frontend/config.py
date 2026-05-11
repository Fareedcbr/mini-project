import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'SQLALCHEMY_DATABASE_URI',
        'mysql+pymysql://root:root@localhost/online_assignments_submission_management_system'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
