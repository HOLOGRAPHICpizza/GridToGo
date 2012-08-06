import os
from twisted.internet import protocol, reactor
from twisted.internet.error import ProcessDone
from twisted.python import log
from gi.repository import Gtk
from gridtogo.client.ui.dialog import *
from twisted.web.client import Agent
from twisted.web.http_headers import Headers

class ConsoleProtocol(protocol.ProcessProtocol):
	def __init__(self, name, logFile, opensimdir, consolePort, callOnEnd=None, callOnOutput=None):
		self.name = name
		self.logFile = logFile
		self.callOnEnd = callOnEnd
		self.callOnOutput = callOnOutput
		self.consolePort = consolePort
		self.opensimdir = opensimdir

		self._buffer = ''

	def connectionMade(self):
		log.msg("Connection Established to child process " + self.name)
		self.pid = self.transport.pid
		
	def childDataReceived(self, fd, data):
		# data is not a complete line, this buffers and only passes complete lines
		if self.callOnOutput:
			data = self._buffer + data
			self._buffer = ''
			for line in data.splitlines(True):
				if line.endswith(('\n', '\r\n')):
					self.callOnOutput(self.name, line.strip())
				else:
					self._buffer = line
	
	def processEnded(self, reason):
		log.msg("Process " + self.name + " has ended. Reason: " + str(reason))

		#TODO: Prevent this dialog from showing if the user initiated the kill
		# Maybe move this dialog stuff somewhere else
		if reason.type is ProcessDone:
			showModalDialog(None, Gtk.MessageType.INFO, 'Process %s exited cleanly.' % self.name)
		else:
			showModalDialog(
				None,
				Gtk.MessageType.ERROR,
				'Process "%s" has exited uncleanly,\nrefer to the logfile %s for details.'
				% (self.name, self.logFile))

		if self.callOnEnd:
			self.callOnEnd(self.name, reason)

	def sendCommand(self):
		"""Sends a command to the REST console of this process."""
		if not hasattr(self, '_session'):
			self._agent = Agent(reactor)
#			self._agent.request(
#				'POST',
#				'http://localhost:%d/StartSession/',)

#TODO: Remove hard-coded path separators and use path.join

def spawnRobustProcess(opensimdir, callOnEnd=None, callOnOutput=None):
	log.msg("Starting ROBUST")

	try:
		os.unlink(opensimdir + '/bin/Robust.log')
	except OSError:
		pass

	p = ConsoleProtocol("ROBUST", opensimdir + '/bin/Robust.log', opensimdir, 8100, callOnEnd, callOnOutput)
	spawnMonoProcess(p, opensimdir + "/bin/" + "Robust.exe", ['-console', 'rest'], opensimdir + "/bin")
	log.msg("Started Robust")
	return p

def spawnRegionProcess(opensimdir, region, consolePort, callOnEnd=None, callOnOutput=None):
	log.msg("Starting Region: " + region)

	try:
		os.unlink(opensimdir + '/bin/OpenSim.log')
	except OSError:
		pass

	p = ConsoleProtocol(region, opensimdir + '/bin/OpenSim.log', opensimdir, consolePort, callOnEnd, callOnOutput)
	spawnMonoProcess(p, opensimdir + "/bin/" + "OpenSim.exe", [
		"-console", "rest"
		"-inimaster=" + opensimdir + "/bin/OpenSim.ini",
		"-inifile=" + opensimdir +"/bin/Regions/" + region + ".ini",
		"-name=" + region
	], opensimdir + "/bin")
	log.msg("Started region: " + region)
	return p

def spawnMonoProcess(protocol, name, args, p):
	if os.name == 'nt':
		#return reactor.spawnProcess(protocol, name, args, path=p)
		raise NotImplementedError('Running on Windows is not yet supported.')
	else:
		log.msg("Args: " + str([name] + args))
		#TODO: Make this not hard-coded to xterm
		return reactor.spawnProcess(
			protocol,
			#"xterm",
			#["xterm", '-fg', 'white', '-bg', 'black', '-sl', '3000', "-e", "mono", name] + args,
			"mono",
			["mono", name] + args,
			path=p,
			env=os.environ)

