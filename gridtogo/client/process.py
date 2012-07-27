import os
from twisted.internet import protocol, reactor
from twisted.python import log
import util

class ConsoleProtocol(protocol.ProcessProtocol):
	def connectionMade(self)
		self.pid = self.transport.pid
		self.window = None
		self.allData = ""
	
	def outReceived(self, data):
		self.allData += data
		if not self.window is None:
			window.updateText()

def spawnRobustProcess(opensimdir):
	log.msg("Starting Robust")
	util.spawnMonoProcess(ConsoleProtocol(), opensimdir + "/bin/" + "Robust.exe", [])
	log.msg("Started Robust")

def spawnRegionProcess(opensimdir, region):
	log.msg("Starting Region: " + region)
	util.spawnRegionProcess(ConsoleProtocol(), opensimdir + "/bin/" + "OpenSim.exe", [
		"-inimaster=" + opensimdir + "/bin/OpenSim.ini",
		"-inifile=" + opensimdir +"/bin/Regions/" + region + ".ini",
		"-name=" + region
	])
	log.msg("Started region: " + region)

def spawnMonoProcess(protocol, name, args):
	if os.name == 'nt':
		return reactor.spawnProcess(protocol, name, args)
	else:
		return reactor.spawnProcess(protocol, "mono", name + args)

