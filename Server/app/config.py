import os

basedir = os.path.abspath(os.path.dirname(__file__))

HOST='0.0.0.0'
PORT=8080
SQLALCHEMY_DATABASE_URI = 'mysql://gps:gpsTrackerP@ssW0rd!@localhost:3306/gps'
SQLALCHEMY_TRACK_MODIFICATIONS = False
MAX_CONTENT_LENGTH = 16 * 1024 * 102
POST_DATA_MAX_SIZE = 1 * 1024 * 1024