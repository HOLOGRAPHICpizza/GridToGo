# module gridtogo.client.opensim.distribution

import httplib
import os.path
import shutil
import string
import sys
import tarfile
from twisted.python import log

import gridtogo.client.ui.windows

VERSION = "0.7.3"

class Distribution(object):
	def __init__(self, projectroot, directory=None, parent=None):
		if directory is None:
			homedir = os.environ["HOME"]
			self.directory = homedir + "/.gridtogo"
		else:
			self.directory = directory

		self.projectroot = projectroot

		self.opensimtar = self.directory + "/opensim.tar.gz"
		self.opensimdir = self.directory + "/opensim"
		self.configdir = self.directory + "/config"
		self.opensimreg = self.directory + "/opensim/bin/Regions"

		self.parent = parent

		self.load()
	
	def load(self):
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

		log.msg("OpenSim Distribution loaded at: " + self.opensimdir)
	
	def configure(self, gridname, ip):
		template = Template(gridname, ip)
		template.run(
			self.projectroot + "/gridtogo/client/opensim/GridCommon.ini",
			self.opensimdir + "/bin/config-include/GridCommon.ini")
		template.run(
			self.projectroot + "/gridtogo/client/opensim/Robust.ini",
			self.opensimdir + "/bin/Robust.ini")
		template.run(
			self.projectroot + "/gridtogo/client/opensim/OpenSim.ini",
			self.opensimdir + "/bin/OpenSim.ini")
		
	def createRegion(self.opensimdir, self.opensimreg, regionName, Location, extHostname):
		#TODO: check for duplicate regions		
		#Create a region's .ini file, then move it to opensim.
		#for knownRegions in self.opensimreg:

			#if regionName + ".ini" == knownRegions:
				#return False

		newRegion = open(regionName + ".ini", 'w')
		newRegion.write("[" + regionName + "]\n")
		UUID = str(uuid.uuid4())
		newRegion.write("RegionUUID = " + UUID  + "\n")
		newRegion.write("Location = " + Location + "\n")
		newRegion.write("InternalAddress = 0.0.0.0\n")
		newRegion.write("InternalPort = 9000\n")
		newRegion.write("AllowAlternatePorts = False\n")
		newRegion.write("ExternalHostname = " + extHostname + "\n")
		
		shutil.copy2(os.path.join(self.opensimdir, regionName + ".ini"), self.opensimreg)
		newRegion.close()
		

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
	def __init__(self, gridname, ip):
		self.gridname = gridname
		self.ip = ip
		log.msg("Template Info: Grid Name = " + gridname + ", IP = " + ip)
	
	def run(self, inloc, outloc):
		log.msg("Template: " + inloc + " -> " + outloc)
		fin = open(inloc, "r")
		fout = open(outloc, "w")

		mappings = {
			"GRID_NAME": self.gridname,
			"IP_ADDRESS": self.ip
			}
		fout.write(string.Template(fin.read()).substitute(mappings))

		fin.close()
		fout.close()

if __name__ == "__main__":
	log.startLogging(sys.stdout)
	dist = Distribution(".", ".gridtogo")
	dist.configure("MyGrid", "localhost")

