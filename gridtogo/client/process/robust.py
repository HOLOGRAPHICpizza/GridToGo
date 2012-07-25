from twisted.internet import protocol, reactor
import util

class RobustProtocol(protocol.ProcessProtocol):
	def connectionMade(self)
		self.pid = self.transport.pid
	
	def outReceived(self, data):
		pass # What to do?

def spawnRobustProcess():
	util.spawnMonoProcess(RobustProtocol(), "Robust.exe", [])
