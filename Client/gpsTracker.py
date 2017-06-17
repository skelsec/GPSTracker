import gps
import time
import multiprocessing
import StringIO
import gzip
from datetime import datetime
import glob
import os

import requests

class GPSPoller(multiprocessing.Process):
	def __init__(self, reportQueue, logQueue):
		multiprocessing.Process.__init__(self)
		self.reportQueue = reportQueue
		self.logQueue = logQueue
		self.gpsd = ''
		
	def setup(self):
		self.gpsd = gps.gps(mode=WATCH_ENABLE|WATCH_JSON)
		
	def self.log(self, level, message):
		self.logQueue.put((level, self.name, message))
		
	def run(self):
		self.setup()
		while True:
			for gpsdata in gpsd.next():
				self.reportQueue.put(gpsdata)
				

class Logger(multiprocessing.Process):
	def __init__(self, logQueue, config):
		multiprocessing.Process.__init__(self)
		self.logQueue = logQueue
		self.config = config
		
	def setup(self):
		return 1
		
	def self.log(self, level, message):
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
		
	def self.log(self, level, message):
		self.logQueue.put((level, self.name, message))
		
		
	def run(self):
		self.setup()
		
		while True:
			gpsdata = self.reportQueue.get()
			with self.gpsDataBufferLock:
				self.gpsDataBuffer.append(gpsdata)
	
	def webSenderThread(self):
		gzipdata = StringIO.StringIO()
		with self.gpsDataBufferLock:
			with gzip.GzipFile(fileobj=gzipdata, mode="wb") as f:
				for gpsdata in self.gpsDataBuffer:
					f.write(gpsdata + '\r\n')
			
			self.gpsDataBuffer = []
		
		try:
			uploader = UploadGPSData(self.config)
			uploader.upload(gzipdata)
		except Exception as e:
			self.log('EXCEPTION', "Error while uploading data to server! Error data:" % (str(e)))
			with open(os.path.join(self.config['REPORTER']['FAILED_UPLOAD_DIR'],'gpsdata_%s.gzip' % (datetime.utcnow()))) as f:
				f.write(gzipdata)
				
		if self.config['REPORTER']['WRITE_GPSDATA_FILE']:
			with open(os.path.join(self.config['REPORTER']['GPSDATA_DIR'],'gpsdata_%s.gzip' % (datetime.utcnow()))) as f:
				f.write(gzipdata)
				
		threading.Timer(self.config['REPORTER']['UPLOADER_FREQ'], self.webSenderThread).start()
			
			
	def reuploaderThread(self):
		for filename in glob.glob(os.path.join(self.config['REPORTER']['FAILED_UPLOAD_DIR'], '*.gzip')):
			with open(filename, 'rb') as f:
				data = f.read()
				try:
					uploader = UploadGPSData(self.config)
					uploader.upload(gzipdata)
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
			
		if r.status_code != requests.codes.ok:
			raise Exception("Server responsed with error! Code: %s" % (r.status_code,) )
		
		return
		
		
		
class GPSTracker()
	def __init__(self, configfile):
		self.reportQueue = multiprocessing.Queue()
		self.logQueue = multiprocessing.Queue()
		self.configfile = configfile
		self.config = ''
		
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
	
	config['REPORTER']['UPLOADER_FREQ']
	config['REPORTER']['GPSDATA_DIR']
	config['REPORTER']['WRITE_GPSDATA_FILE']
	config['REPORTER']['FAILED_UPLOAD_DIR']
	config['REPORTER']['REUPLOADER_FREQ']
	config['UPLOADER']['UPLOAD_URL']
	config['UPLOADER']['CLIENT_CERT']
	config['UPLOADER']['CLIENT_KEY']
	config['UPLOADER']['TIMEOUT']
		
	
	
	gpst = GPSTracker(config)
	gpst.run()
	