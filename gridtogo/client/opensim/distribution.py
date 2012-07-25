# module gridtogo.client.opensim.distribution

import os.path

class Distribution(object):
	def __init__(directory):
		self.opensimtar = directory + "/opensim.tar.gz"
		self.opensimdir = directory + "/opensim"

		if not os.path.isdir(self.opensimdir):
			if not os.path.isfile(self.opensimtar):
				download()
			extract()
		
	def download(self):
		pass
		
	def extract(self):
		pass
