#distribution.py
#Downloads OpenSim, moves it, and packs in the files we need it to have
# module gridtogo.client.opensim.distribution

if __name__ == "__main__":
	from twisted.internet import gtk3reactor
	gtk3reactor.install()

from gi.repository import Gtk
import os.path
import shutil
import socket
import string
import sys
import tarfile
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
import uuid

VERSION = "0.7.3"

# It is okay to have more than one Distribution with the same directory, as
# long as you don't do anything stupid like try to create the same file with
# both...
class Distribution(object):
	def __init__(self, projectroot, directory=None, parent=None):
		#Place the OpenSim distribution into a place where  the GridToGo program can find it
		#TODO: Make all paths use path.join and whatnot instead of hard-coding separators
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
	
	# Loads asynchonously and passes self to the deferred
	def load(self, deferred):
		self.loaddeferred = deferred
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
			else:
				self.continueload()

	def continueload(self):
		if not os.path.isdir(self.opensimdir):
			self.extract()

		if not os.path.isdir(self.regionsdir):
			log.msg("Creating directory: " + self.regionsdir)
			os.mkdir(self.regionsdir)

		if not os.path.isdir(self.userconfigdir):
			log.msg("Creating directory: " + self.userconfigdir)
			os.mkdir(self.userconfigdir)

		# Create an empty ConsoleClient config file, it needs this for some dumb reason
		open(os.path.join(self.opensimdir, 'bin', 'OpenSim.ConsoleClient.ini'), 'w').close()

		log.msg("OpenSim Distribution loaded at: " + self.opensimdir)
		self.loaddeferred.callback(self)
	
	def configure(self, gridname, ip):
		"""This does region-agnostic configuration."""

		mappings = {
			"GRID_NAME": gridname,
			"IP_ADDRESS": ip
		}

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
			open(self.configdir + "/Robust.ini", "w").close()

		template = Template(mappings)
		template.run(
			self.projectroot + "/gridtogo/client/opensim/Robust.ini",
			self.opensimdir + "/bin/Robust.ini")
		template.run(
			self.configdir + "/Robust.ini",
			self.userconfigdir + "/Robust.ini")

		log.msg("Configured Robust")
		
	def configureRegion(self, regionName, location, port):
		"""This does region-specific configuration."""
		mappings = { "NAME": regionName,
					 "LOCATION": location,
					 "EXTERNAL_HOSTNAME": self.clientObject.externalhostname,
					 "PORT": port,
		             "CONSOLE_PORT": port + 10000,
					 "UUID": str(uuid.uuid4()) }

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

		log.msg("Requesting file: /opensim-" + VERSION + ".tar.gz")

		self.versionedtar = self.directory + "/opensim-" + VERSION + ".tar.gz"
		log.msg("Download & Writing file: " + self.versionedtar)

		self.tarhandle = open(self.versionedtar, "w")

		agent = Agent(reactor)
		d = agent.request('GET', 'http://dist.opensimulator.org/opensim-' + VERSION +'.tar.gz', Headers({'User-Agent': ['GridToGo']}), None)
		d.addCallback(self.request)
	
	def request(self, response):
		log.msg("Received Request's Response")
		response.deliverBody(DownloadProtocol(self, response.length))

	def donedownload(self):
		self.tarhandle.close()
		log.msg("Wrote file: " + self.versionedtar)

		if sys.platform != "win32":
			os.symlink(self.versionedtar, self.opensimtar)
			log.msg("Created symlink: " + self.versionedtar + " -> " + self.opensimtar)
		else:
			log.msg("FileSystem does not allow symlinks, moving directory instead")
			os.rename(self.versionedtar, self.opensimtar)
			log.msg("Rename: " + self.versionedsimtar + " -> " + self.opensimtar)

		self.continueload()
		
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

class DownloadProtocol(Protocol):
	def __init__(self, dist, size):
		self.dist = dist
		self.size = float(size)
		self.progress = 0.0
		self.window = Gtk.Window()
		self.progressbar = Gtk.ProgressBar()
		self.label = Gtk.Label("Downloading OpenSim")
		self.box = Gtk.VBox()
		self.box.pack_start(self.label, False, False, 0)
		self.box.pack_start(self.progressbar, False, False, 0)
		self.window.add(self.box)
		self.window.set_size_request(400, 50)
		self.window.show_all()
	
	def dataReceived(self, data):
		self.progress += len(data)
		self.progressbar.set_fraction(self.getPercent())
		self.dist.tarhandle.write(data)
	
	def connectionLost(self, reason):
		log.msg("Finished receiving data: " + reason.getErrorMessage())
		self.window.destroy()
		self.dist.donedownload()
	
	def getPercent(self):
		return self.progress / self.size

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

def testdone(dist):
	dist.configure("MyGrid", "localhost")

def start(*args):
	log.startLogging(sys.stdout)
	dist = Distribution(os.path.abspath("."), os.path.abspath(".gridtogo"))
	d = Deferred()
	d.addCallback(testdone)
	dist.load(d)

if __name__ == "__main__":
	reactor.callWhenRunning(start)
	reactor.run()
