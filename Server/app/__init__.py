from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api
from flask_cors import CORS

app = Flask(__name__)
app.config.from_pyfile('config.py')
CORS(app)
api = Api(app)
db = SQLAlchemy(app)

from gpsTrackerServer import ClientReciever, GetLatestPosition, GetPosition


api.add_resource(ClientReciever, '/gpstracker/upload/<string:client_name>')
api.add_resource(GetLatestPosition, '/gpstracker/position/<string:client_name>/latest')
api.add_resource(GetPosition, '/gpstracker/position/<string:client_name>/<string:start_date>/<string:end_date>/<int:interval>')
