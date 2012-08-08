import os
from twisted.internet import protocol, reactor
from twisted.internet.protocol import Protocol
from twisted.internet.defer import succeed
from twisted.internet.error import ProcessDone
from twisted.python import log
from gi.repository import Gtk
from gridtogo.client.ui.dialog import *
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
import urllib
import xml.dom.minidom
from zope.interface import implements

class PostProducer(object):
	implements(IBodyProducer)

	def __init__(self, values):
		self.body = urllib.urlencode(values)
		self.length = len(self.body)
	
	def startProducing(self, consumer):
		consumer.write(self.body)
		return succeed(None)
	
	def pauseProducing(self):
		pass
	
	def stopProducing(self):
		pass

class ConsoleProtocol(protocol.ProcessProtocol):
	def __init__(self, name, logFile, opensimdir, consolePort, externalhost, callOnEnd=None, callOnOutput=None):
		self.name = name
		self.logFile = logFile
		self.callOnEnd = callOnEnd
		self.callOnOutput = callOnOutput
		self.consolePort = consolePort
		self.opensimdir = opensimdir
		self.externalhost = externalhost

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

	def sendCommand(self, url, attrs, callback=None):
		"""Sends a command to the REST console of this process."""
		log.msg("[REST] Sending command: /" + url)
		if not hasattr(self, '_sessionid'):
			log.msg("[REST] [SESSION] Fetching Session ID")
			agent = Agent(reactor)
			d = agent.request(
				'POST',
				'http://%s:%d/StartSession/' % (str(self.externalhost), self.consolePort),
				Headers({"Content-Type": ["application/x-www-form-urlencoded"]}),
				PostProducer({
					"USER": "gridtogo",
					"PASS": "gridtogopass"
				}))

			def request(response):
				response.deliverBody(CommandProtocol(response.length, done))

			def err(response):
				log.msg("[REST] [SESSION] [ERROR] " + str(response))
				
			def done(protocol):
				def getText(nodelist):
					rc = []
					for node in nodelist:
						if node.nodeType == node.TEXT_NODE:
							rc.append(node.data)
					return ''.join(rc)

				xmldata = protocol.alldata
				xmlstr = str(bytearray(xmldata))
				log.msg("[REST] [SESSION] Received: " + xmlstr)
				dom = xml.dom.minidom.parseString(xmlstr)
				self.sessionid = getText(dom.getElementsByTagName("ConsoleSession")[0].getElementsByTagName("SessionID")[0].childNodes)
				log.msg("[REST] [SESSION] Session ID = " + self.sessionid)
				self.sendCommand2(url, attrs, callback)
				
			d.addCallback(request)
			d.addErrback(err)
		else:
			self.sendCommand2(url, attrs, callback)

	def sendCommand2(self, url, attrs, callback=None):
		agent = Agent(reactor)
		d = agent.request(
			'POST',
			('http://%s:%d/' % (str(self.externalhost), self.consolePort)) + url,
			Headers({"Content-Type": ["application/x-www-form-urlencoded"]}),
			PostProducer(attrs))

		def request(response):
			log.msg("[REST] Received response")
			callback(response)

		def err(response):
			log.msg("[REST] [ERROR] " + str(response))

		if not callback is None:
			d.addCallback(request)
		
		d.addErrback(err)

class CommandProtocol(Protocol):
	def __init__(self, size, callback):
		self.size = size
		self.alldata = []
		self.callback = callback

	def dataReceived(self, data):
		self.alldata += data
	
	def connectionLost(self, reason):
		log.msg("[REST] Connection Lost. Reason: " + str(reason))
		self.callback(self)

#TODO: Remove hard-coded path separators and use path.join

def spawnRobustProcess(opensimdir, externalhost, callOnEnd=None, callOnOutput=None):
	log.msg("Starting ROBUST")

	try:
		os.unlink(opensimdir + '/bin/Robust.log')
	except OSError:
		pass

	p = ConsoleProtocol("ROBUST", opensimdir + '/bin/Robust.log', opensimdir, 18000, externalhost, callOnEnd, callOnOutput)
	spawnMonoProcess(p, opensimdir + "/bin/" + "Robust.exe", ['-console', 'rest'], opensimdir + "/bin")
	log.msg("Started Robust")
	return p

def spawnRegionProcess(opensimdir, region, consolePort, externalhost, callOnEnd=None, callOnOutput=None):
	log.msg("Starting Region: " + region)

	try:
		os.unlink(opensimdir + '/bin/OpenSim.log')
	except OSError:
		pass

	p = ConsoleProtocol(region, opensimdir + '/bin/OpenSim.log', opensimdir, consolePort, externalhost, callOnEnd, callOnOutput)
	spawnMonoProcess(p, opensimdir + "/bin/" + "OpenSim.exe", [
		"-inimaster=" + opensimdir + "/bin/OpenSim.ini",
		"-inifile=" + opensimdir +"/bin/Regions/" + region + ".ini",
		"-console=rest",
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

