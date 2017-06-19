import os

basedir = os.path.join(os.path.abspath(os.path.dirname(__file__)),'..')

WEBPAGE_DIR = os.path.join(basedir,'static')
HOST='0.0.0.0'
PORT=8080
SQLALCHEMY_DATABASE_URI = 'mysql://gps:gpsTrackerP@ssW0rd!@localhost:3306/gps'
SQLALCHEMY_TRACK_MODIFICATIONS = False
MAX_CONTENT_LENGTH = 16 * 1024 * 102
POST_DATA_MAX_SIZE = 1 * 1024 * 1024
