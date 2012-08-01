import os
from twisted.internet import protocol, reactor
from twisted.python import log

class ConsoleProtocol(protocol.ProcessProtocol):
	def __init__(self, name):
		self.name = name
		self.allData = ""
		self.window = None

	def connectionMade(self):
		log.msg("Connection Established with " + self.name)
		self.pid = self.transport.pid
		
	def childDataReceived(self, fd, data):
		self.allData += data
		if not self.window is None:
			self.window.outReceived(data)
	
	def processEnded(self, reason):
		log.msg("Process " + self.name + " has ended. Reason: " + str(reason))

def spawnRobustProcess(opensimdir):
	log.msg("Starting Robust")
	p = ConsoleProtocol("Robust")
	spawnMonoProcess(p, opensimdir + "/bin/" + "Robust.exe", [], opensimdir + "/bin")
	log.msg("Started Robust")
	return p

def spawnRegionProcess(opensimdir, region):
	log.msg("Starting Region: " + region)
	p = ConsoleProtocol("OpenSim")
	spawnMonoProcess(ConsoleProtocol("OpenSim"), opensimdir + "/bin/" + "OpenSim.exe", [
		"-inimaster=" + opensimdir + "/bin/OpenSim.ini",
		"-inifile=" + opensimdir +"/bin/Regions/" + region + ".ini",
		"-name=" + region
	], opensimdir + "/bin")
	log.msg("Started region: " + region)
	return p

def spawnMonoProcess(protocol, name, args, p):
	if os.name == 'nt':
		return reactor.spawnProcess(protocol, name, args, path=p)
	else:
		log.msg("Args: " + str([name] + args))
		#TODO: Make this not hard-coded to xterm
		return reactor.spawnProcess(
			protocol,
			"xterm",
			["xterm", '-fg', 'white', '-bg', 'black', '-sl', '3000', "-e", "mono", name] + args,
			path=p,
			env=os.environ)

