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
		self.url = config['UPLOADER']['UPLOAD_URL']
		self.clientCert = config['UPLOADER']['CLIENT_CERT']
		self.clientKey = config['UPLOADER']['CLIENT_KEY']
		self.timeout = config['UPLOADER']['TIMEOUT']
		
	def upload(self, data):
		if self.clientCert == '' or self.clientKey == '':
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
	def __init__(self, configfile = '', config = ''):
		self.reportQueue = multiprocessing.Queue()
		self.logQueue = multiprocessing.Queue()
		self.configfile = configfile
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
	
	config = {}
	config['REPORTER'] = {}
	config['UPLOADER'] = {}
	config['REPORTER']['UPLOADER_FREQ'] = 10
	config['REPORTER']['GPSDATA_DIR']   = '/root/gpsdata'
	config['REPORTER']['WRITE_GPSDATA_FILE'] = True
	config['REPORTER']['FAILED_UPLOAD_DIR'] = '/root/gpsdata/failed'
	config['REPORTER']['REUPLOADER_FREQ'] = 15
	config['UPLOADER']['UPLOAD_URL'] = 'http://192.168.4.70:8080/gpstracker/upload/testgps'
	config['UPLOADER']['CLIENT_CERT'] = ''
	config['UPLOADER']['CLIENT_KEY']  = ''
	config['UPLOADER']['TIMEOUT']     = 20

	print config		
	
	
	gpst = GPSTracker(config = config)
	gpst.run()
	
