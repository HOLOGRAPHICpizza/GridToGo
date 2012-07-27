#distribution.py
#Downloads OpenSim, moves it, and packs in the files we need it to have
# module gridtogo.client.opensim.distribution

import httplib
import os.path
import shutil
import string
import sys
import tarfile
from twisted.python import log
import uuid

import gridtogo.client.ui.windows

VERSION = "0.7.3"

# It is okay to have more than one Distribution with the same directory, as
# long as you don't do anything stupid like try to create the same file with
# both...
class Distribution(object):
	def __init__(self, projectroot, directory=None, parent=None):
		#Place the OpenSim distribution into a place where  the GridToGo program can find it
		if directory is None:
			homedir = os.environ["HOME"]
			self.directory = homedir + "/.gridtogo"
		else:
			self.directory = directory

		self.projectroot = projectroot

		self.opensimtar = self.directory + "/opensim.tar.gz"
		self.opensimdir = self.directory + "/opensim"
		self.configdir = self.directory + "/config"
		self.userconfigdir = self.opensimdir + "/bin/config-include/userconfig"
		self.regionsdir = self.directory + "/opensim/bin/Regions"

		self.parent = parent

		self.load()
	
	def load(self):
		# Loads OpenSim and creates the directory to load it into
		log.msg("OpenSim Distribution loading at: " + self.opensimdir)

		if not os.path.isdir(self.directory):
			log.msg("Creating directory: " + self.directory)
			os.mkdir(self.directory)

		if not os.path.isdir(self.configdir):
			log.msg("Creating directory: " + self.configdir)
			os.mkdir(self.configdir)

		if not os.path.isdir(self.opensimdir):
			if not os.path.isfile(self.opensimtar):
				self.download()
			self.extract()

		if not os.path.isdir(self.regionsdir):
			log.msg("Creating directory: " + self.regionsdir)
			os.mkdir(self.regionsdir)

		if not os.path.isdir(self.userconfigdir):
			log.msg("Creating directory: " + self.userconfigdir)
			os.mkdir(self.userconfigdir)

		log.msg("OpenSim Distribution loaded at: " + self.opensimdir)
	
	def configure(self, gridname, ip):
		mappings = { "GRID_NAME": gridname, "IP_ADDRESS": ip }
		log.msg("Configuring Region-Agnostic Configuration")
		if not os.path.isfile(self.configdir + "/GridCommon.ini"):
			log.msg("Create file: " + self.configdir + "/GridCommon.ini")
			open(self.configdir + "/GridCommon.ini", "w").close()
		if not os.path.isfile(self.configdir + "/OpenSim.ini"):
			log.msg("Create file: " + self.configdir + "/OpenSim.ini")
			open(self.configdir + "/OpenSim.ini", "w").close()

		template = Template(mappings)
		template.run(
			self.projectroot + "/gridtogo/client/opensim/GridCommon.ini",
			self.opensimdir + "/bin/config-include/GridCommon.ini")
		template.run(
			self.projectroot + "/gridtogo/client/opensim/OpenSim.ini",
			self.opensimdir + "/bin/OpenSim.ini")
		template.run(
			self.configdir + "/GridCommon.ini",
			self.userconfigdir + "/GridCommon.ini")
		template.run(
			self.configdir + "/OpenSim.ini",
			self.userconfigdir + "/OpenSim.ini")
		log.msg("Configured Region-Agnostic Configuration")
	
	def configureRobust(self, gridname, ip):
		mappings = { "GRID_NAME": gridname, "IP_ADDRESS": ip }
		log.msg("Configuring Robust")
		if not os.path.isfile(self.configdir + "/Robust.ini"):
			log.msg("Create file: " + self.configdir + "/Robust.ini")
			open(self.configdir + "/Robust.ini").close()

		template = Template(mappings)
		template.run(
			self.projectroot + "/gridtogo/client/opensim/Robust.ini",
			self.opensimdir + "/bin/Robust.ini")
		template.run(
			self.configdir + "/Robust.ini",
			self.userconfigdir + "/Robust.ini")

		log.msg("Configured Robust")
		
	def configureRegion(self, regionName, location, extHostname, port):
		mappings = { "NAME": regionName,
					 "LOCATION": location,
					 "EXTERNAL_HOSTNAME": extHostname,
					 "PORT": port,
					 "UUID": uuid.uuid4() }
		template = Template(mappings)
		if not os.path.isfile(self.configdir + "/Region.ini"):
			log.msg("Create file: " + self.configdir + "/Region.ini")
			open(self.configdir + "/Region.ini", "w").close()
		if not os.path.isfile(self.configdir + "/Regions.ini"):
			log.msg("Create file: " + self.configdir + "/Regions.ini")
			open(self.configdir + "/Regions.ini", "w").close()
		if not os.path.isfile(self.configdir + "/" + regionName + ".ini"):
			log.msg("Create file: " + self.configdir + "/" + regionName + ".ini")
			open(self.configdir + "/" + regionName + ".ini", "w").close()
			
		log.msg("Configuring Region: " + regionName)

		template.run(
			self.projectroot + "/gridtogo/client/opensim/Region.ini",
			self.regionsdir + "/" + regionName + ".ini")
		if not os.path.isdir(self.regionsdir + "/" + regionName):
			log.msg("Create directory: " + self.regionsdir + "/" + regionName)
			os.mkdir(self.regionsdir + "/" + regionName)
		template.run(
			self.projectroot + "/gridtogo/client/opensim/Regions.ini",
			self.regionsdir + "/" + regionName + "/Regions.ini")
		template.run(
			self.configdir + "/Region.ini",
			self.userconfigdir + "/Region.ini")
		template.run(
			self.configdir + "/Regions.ini",
			self.userconfigdir + "/Regions.ini")
		template.run(
			self.configdir + "/" + regionName + ".ini",
			self.userconfigdir + "/" + regionName + ".ini")
		log.msg("Configured Region: " + regionName)

	def download(self):
		log.msg("Downloading file: " + self.opensimtar)
		log.msg("Establishing connection to: dist.opensimulator.org")
		connection = httplib.HTTPConnection("dist.opensimulator.org")
		log.msg("Established connection to: dist.opensimulator.org")

		log.msg("Requesting file: /opensim-" + VERSION + ".tar.gz")
		connection.request("GET", "/opensim-" + VERSION + ".tar.gz")
		response = connection.getresponse()
		if response.status != 200:
			log.err("Bad Response from Server: " + str(response.status))

		versionedtar = self.directory + "/opensim-" + VERSION + ".tar.gz"
		log.msg("Download & Writing file: " + versionedtar)
		f = open(versionedtar, "w")
		f.write(response.read())
		f.close()
		log.msg("Wrote file: " + versionedtar)

		if sys.platform != "win32":
			os.symlink(versionedtar, self.opensimtar)
			log.msg("Created symlink: " + versionedtar + " -> " + self.opensimtar)
		else:
			log.msg("FileSystem does not allow symlinks, moving directory instead")
			os.rename(versionedtar, opensimtar)
			log.msg("Rename: " + versionedsimtar + " -> " + self.opensimtar)
		
	def extract(self):
		#Extract OpenSim from the .tar file that contains it
		log.msg("Extracting file: " + self.opensimtar)
		tar = tarfile.open(self.opensimtar)
		tar.extractall(self.directory)
		tar.close()
		log.msg("Extracted file: " + self.opensimtar)

		olddir = self.directory + "/opensim-" + VERSION
		newdir = self.directory + "/opensim"

		if sys.platform != "win32":
			if os.path.isdir(olddir):
				os.symlink(olddir, newdir)
				log.msg("Created symlink: " + olddir + " -> " + newdir)
			else:
				log.err("Tar file extracted wrong version. Please symlink manually")
		else:
			log.msg("FileSystem does not allow symlinks, moving directory instead")
			os.rename(olddir, newdir)
			log.msg("Rename: " + olddir + " -> " + newdir)



class Template(object):
	def __init__(self, mappings):
		self.mappings = mappings
	
	def run(self, inloc, outloc):
		log.msg("Template: " + inloc + " -> " + outloc)
		fin = open(inloc, "r")
		fout = open(outloc, "w")

		fout.write(AtTemplate(fin.read()).substitute(self.mappings))

		fin.close()
		fout.close()

class AtTemplate(string.Template):
	delimiter = "@"

if __name__ == "__main__":
	log.startLogging(sys.stdout)
	dist = Distribution(".", ".gridtogo")
	dist.configure("MyGrid", "localhost")

