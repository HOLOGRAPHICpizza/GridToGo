# module gridtogo.client.opensim.distribution

import httplib
import os.path
import sys
import tarfile
from twisted.python import log

VERSION = "2.7.3"

class Distribution(object):
	def __init__(directory):
		self.directory = directory
		self.opensimtar = directory + "/opensim.tar.gz"
		self.opensimdir = directory + "/opensim"
	
	def load(self):
		log.msg("OpenSim Distribution loading at: " + self.opensimdir)

		if not os.path.isdir(self.directory):
			log.msg("Creating directory: " + self.directory)

		if not os.path.isdir(self.opensimdir):
			log.msg("Creating directory: " + self.opensimdir)

		if not os.path.isfile(self.opensimtar):
			download()

		extract()

		log.msg("OpenSim Distribution loaded at: " + self.opensimdir)
		
	def download(self):
		log.msg("Downloading file: " + self.opensimtar)
		log.msg("Establishing connection to: dist.opensim.org")
		connection = httplib.HTTPConnection("dist.opensim.org")
		log.msg("Established connection to: dist.opensim.org")

		log.msg("Requesting file: opensim-" + VERSION + ".tar.gz")
		connection.request("opensim-" + VERSION + ".tar.gz")
		response = connection.getresponse()
		log.msg("Finished downloading: opensim-" + VERSION + ".tar.gz")

		log.msg("Writing file: " + self.opensimtar)
		f = open(self.opensimtar, "w")
		f.write(response.read())
		f.close()
		log.msg("Wrote file: " + self.opensimtar)
		pass
		
	def extract(self):
		log.msg("Extracting file: " + self.opensimtar)
		tar = tarfile.open(self.opensimtar)
		tar.extract(self.opensimdir)
		tar.close()
		log.msg("Extracted file: " + self.opensimtar)
		pass

if __name__ == "__main__":
	log.startLogging(sys.stdout)
	Distribution("/home/jared/.gridtogo").load()
