from twisted.internet import protocol, reactor
from gridtogo.server.process.util import spawnMonoProcess

class RobustProtocol(protocol.ProcessProtocol):
	def connectionMade(self)
		self.pid = self.transport.pid
	
	def outReceived(self, data):
		pass # What to do?

def spawnRobustProcess():
	spawnMonoProcess(RobustProtocol(), "Robust.exe", [])
