#!/usr/bin/env python
import time
import threading
import multiprocessing
import cStringIO
import gzip
from datetime import datetime
import glob
import os
import json
import shutil


import gps
import requests


class DictWrapperEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, gps.dictwrapper):
			return dict(obj)
		
		return json.JSONEncoder.default(self.obj)

class GPSPoller(multiprocessing.Process):
	def __init__(self, reportQueue, logQueue, config):
		multiprocessing.Process.__init__(self)
		self.reportQueue = reportQueue
		self.logQueue = logQueue
		self.gpsd = ''
		
	def setup(self):
		self.gpsd = gps.gps()
		self.gpsd.stream(gps.WATCH_ENABLE|gps.WATCH_NEWSTYLE)

	def log(self, level, message):
		self.logQueue.put((level, self.name, message))
		
	def run(self):
		self.setup()
		while True:
			for gpsdata in self.gpsd:
				self.reportQueue.put(json.dumps(gpsdata, cls=DictWrapperEncoder))
				

class Logger(multiprocessing.Process):
	def __init__(self, logQueue, config):
		multiprocessing.Process.__init__(self)
		self.logQueue = logQueue
		self.config = config
		
	def setup(self):
		return 1
		
	def log(self, level, message):
		self.logQueue.put((level, self.name, message))
		
	def run(self):
		self.setup()
		while True:
			log = self.logQueue.get()
			self.handleLog(log)
			
	def handleLog(self, log):
		level, src, message = log
		print '[%s][%s][%s] %s' % (datetime.utcnow(), level, src, message)
		
		
class ReportHandler(multiprocessing.Process):
	def __init__(self, reportQueue, logQueue, config):
		multiprocessing.Process.__init__(self)
		self.reportQueue = reportQueue
		self.logQueue = logQueue
		self.config = config
		
		self.gpsDataBuffer = []
		self.gpsDataBufferLock = threading.Lock()
		
	def setup(self):
		threading.Timer(self.config['REPORTER']['UPLOADER_FREQ'], self.webSenderThread).start()
		threading.Timer(self.config['REPORTER']['REUPLOADER_FREQ'], self.reuploaderThread).start()
		
	def log(self, level, message):
		self.logQueue.put((level, self.name, message))
		
		
	def run(self):
		self.setup()
		
		while True:
			gpsdata = self.reportQueue.get()
			with self.gpsDataBufferLock:
				self.gpsDataBuffer.append(gpsdata)
	
	def webSenderThread(self):
		gzipdata = cStringIO.StringIO()
		with self.gpsDataBufferLock:
			with gzip.GzipFile(fileobj=gzipdata, mode="wb") as f:
				for gpsdata in self.gpsDataBuffer:
					f.write(gpsdata + '\r\n')
			
			self.gpsDataBuffer = []
			gzipdata.seek(0)
		try:
			uploader = UploadGPSData(self.config)
			uploader.upload(gzipdata.getvalue())
		except Exception as e:
			self.log('EXCEPTION', "Error while uploading data to server! Error data: %s" % (str(e)))
			with open(os.path.join(self.config['REPORTER']['FAILED_UPLOAD_DIR'],'gpsdata_%s.gzip' % (datetime.utcnow().strftime("%Y%m%d-%H%M%S"))),'wb') as f:
				gzipdata.seek(0)
				shutil.copyfileobj(gzipdata,f)
				
		if self.config['REPORTER']['WRITE_GPSDATA_FILE']:
			with open(os.path.join(self.config['REPORTER']['GPSDATA_DIR'],'gpsdata_%s.gzip' % (datetime.utcnow().strftime("%Y%m%d-%H%M%S"))),'wb') as f:
				gzipdata.seek(0)
				shutil.copyfileobj(gzipdata,f)
				
		threading.Timer(self.config['REPORTER']['UPLOADER_FREQ'], self.webSenderThread).start()
			
			
	def reuploaderThread(self):
		for filename in glob.glob(os.path.join(self.config['REPORTER']['FAILED_UPLOAD_DIR'], '*.gzip')):
			with open(filename, 'rb') as f:
				data = f.read()
				try:
					uploader = UploadGPSData(self.config)
					uploader.upload(data)
				except Exception as e:
					break
			
			os.remove(filename)
			
		threading.Timer(self.config['REPORTER']['REUPLOADER_FREQ'], self.reuploaderThread).start()
			
			
		
class UploadGPSData():
	def __init__(self, config):
		self.url = config['UPLOADER']['UPLOAD_URL'] + config['UPLOADER']['CLIENT_NAME']
		self.clientCert = config['UPLOADER']['CLIENT_CERT']
		self.clientKey = config['UPLOADER']['CLIENT_KEY']
		self.timeout = config['UPLOADER']['TIMEOUT']
		
	def upload(self, data):
		if self.url[:5].lower() != 'https' or self.clientCert == '' or self.clientKey == '':
			res = requests.post(
					url=self.url,
                    data=data,
                    headers={'Content-Type': 'application/octet-stream'},
					timeout=self.timeout)
		else:
			res = requests.post(
					url=self.url,
                    data=data,
                    headers={'Content-Type': 'application/octet-stream'},
					timeout=self.timeout,
					cert=(self.clientCert, self.clientKey))
			
		if res.status_code != requests.codes.ok:
			raise Exception("Server responsed with error! Code: %s" % (res.status_code,) )
		
		return
		
		
		
class GPSTracker():
	def __init__(self, config):
		self.reportQueue = multiprocessing.Queue()
		self.logQueue = multiprocessing.Queue()
		self.config = config

		
	def setup(self):
		self.logger = Logger(self.logQueue, self.config)
		self.logger.daemon = True
		self.logger.start()
		
		self.poller = GPSPoller(self.reportQueue, self.logQueue, self.config)
		self.poller.daemon = True
		self.poller.start()
		
		self.reporter = ReportHandler(self.reportQueue, self.logQueue, self.config)
		self.reporter.daemon = True
		self.reporter.start()
	
	def run(self):
		self.setup()
		while True:
			time.sleep(10)
			
			
if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")
	parser.add_argument("-c", "--config", help="Config file", default = '')
	parser.add_argument("-u", type = int, help= 'Upload fequency', default = 60)
	parser.add_argument("-g", help= 'Directory to keep GPS data in', default = './')
	parser.add_argument("-w", help= 'Keep local copy of GPS data', action="store_true")
	parser.add_argument("-f", help= 'Directory to store failed uploads', default = './failed/')
	parser.add_argument("-r", type = int, help= 'Reupload  retry frequency', default = 60)
	parser.add_argument("--upload-url",  help= 'GPSTracker web service URL', default = 'http://127.0.0.1/')
	parser.add_argument("--client-cert", help= 'Client cert file for upload SSL auth', default = './certs/client.pem')
	parser.add_argument("--client-key",  help= 'Client key file for upload SSL auth', default = './certs/client.key')
	parser.add_argument("-t", "--timeout", type = int, help= 'Data file upload timeout', default = 10)
	
	args = parser.parse_args()
	if args.config != '':
		with open(args.config, 'rb') as f:
			config = json.loads(f.read())
	
	else:
		config = {}
		config['REPORTER'] = {}
		config['UPLOADER'] = {}
		config['REPORTER']['UPLOADER_FREQ'] = args.u
		config['REPORTER']['GPSDATA_DIR']   = args.g
		config['REPORTER']['WRITE_GPSDATA_FILE'] = args.w
		config['REPORTER']['FAILED_UPLOAD_DIR'] = args.f
		config['REPORTER']['REUPLOADER_FREQ'] = args.r
		config['UPLOADER']['UPLOAD_URL'] = args.upload_url
		config['UPLOADER']['CLIENT_CERT'] = args.client-cert
		config['UPLOADER']['CLIENT_KEY']  = args.client-key
		config['UPLOADER']['TIMEOUT']     = args.t
	
	
	gpst = GPSTracker(config = config)
	gpst.run()
	
