#!/usr/bin/env python
from flask import Flask, request
from flask_restful import Resource, Api
from sqlalchemy import create_engine
import json
import gzip
import cStringIO



e = create_engine('mysql://gps:gpsTrackerP@ssW0rd!@localhost:3306/gps')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


api = Api(app)
		

class ClientReciever(Resource):
    def post(self, client_name):
		conn = e.connect()
		if request.content_length is not None and request.content_length > config['POST_DATA_MAX_SIZE']:
			#log
			return 'Error'
		try:
			compressedFile = cStringIO.StringIO(request.get_data())
			compressedFile.seek(0)
			with decompressedFile as gzip.GzipFile(fileobj=compressedFile, mode='rb'):
				for line in decompressedFile:
					line = line.strip()
					try:
						gpsdata = json.loads(line)
						if 'class' not in gpsdata:
							print 'Strange!'
							return 'Error'
						
						if gpsdata['class'] == 'TPV':
							
						
						# log raw data as json
						query = conn.execute("select * from salaries where Department='%s'"%department_name.upper())
						
						#parse dictionary, and insert the formatted data in a different table
						query = conn.execute("select * from salaries where Department='%s'"%department_name.upper())
						
					except:
						#log
						return 'Error'
			
			
			
		except:
			#log
			return 'Error'
	

 
api.add_resource(ClientReciever, '/gpstracker/upload/<string:client_name>')

if __name__ == '__main__':
	app.run()