import socket
import string
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, ClientFactory, Factory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
import random

from gridtogo.shared.networkobjects import *

class EchoProtocol(Protocol):
	def __init__(self, factory, port):
		self.factory = factory
		self.port = port
	
	def connectionMade(self):
		log.msg("[NAT] Established Connection on port " + str(self.port))
	
	def connectionLost(self, reason):
		log.msg("[NAT] Lost Connection on port " + str(self.port) + ". Reason: " + str(reason))

	def close(self):
		self.transport.loseConnection()
	
	def dataReceived(self, data):
		self.transport.write(data)

class EchoFactory(Factory):
	def __init__(self, builder, port):
		self.builder = builder
		self.port = port

	def buildProtocol(self, addr):
		protocol = EchoProtocol(self, self.port)
		return protocol

class EchoFactoryBuilder(object):
	def __init__(self, service):
		self.service = service

	def buildFactory(self, port):
		return EchoFactory(self, port)

class EchoService(object):
	def __init__(self):
		log.msg("[NAT] Creating Echo Service")
	
	def start(self, deferred, finalCount, ports):
		log.msg("[NAT] Starting Echo Service")
		self.builder = EchoFactoryBuilder(self)
		self.connections = []
		self.connectionCount = 0
		self.deferred = deferred
		self.finalCount = finalCount
		for port in ports:
			self.listenOn(port)
	
	def listenOn(self, port):
		log.msg("[NAT] Listening on port " + str(port))
		endpoint = TCP4ServerEndpoint(reactor, port)
		d = endpoint.listen(self.builder.buildFactory(port))
		d.addCallback(self.portStarted)
	
	def portStarted(self, connection):
		log.msg("[NAT] A port server has been successfully established.")
		self.connections += [connection]
		self.connectionCount += 1
		if self.connectionCount == self.finalCount:
			self.deferred.callback(self)
	
	def close(self):
		log.msg("[NAT] Closing Echo Service")
		for connection in self.connections:
			connection.stopListening()

class EchoClient(LineReceiver):
	def __init__(self, callback):
		self.code = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(16))
		self.callback = callback
		self.timedout = False
		self.done = False

	def connectionMade(self):
		self.sendLine(self.code)
		reactor.callLater(5, self.timeout)
	
	def lineReceived(self, line):
		if not self.timedout and not self.done:
			if(line == self.code):
				log.msg("[NAT] Message Matches")
				self.done = True
				self.callback(True)
			else:
				log.msg("[NAT] Message doesn't match. Stop trolling.")
				self.done = True
				self.callback(False)
		self.transport.loseConnection()
	
	def timeout(self):
		if not self.done:
			log.msg("[NAT] Client Timeout")
			self.callback(False)
			self.transport.loseConnection()

class EchoClientFactory(ClientFactory):
	protocol = EchoClient

	def __init__(self, callback):
		self.callback = callback

	def buildProtocol(self, addr):
		return EchoClient(self.callback)

	def clientConnectionFailed(self, connector, reason):
		log.msg("NAT Echo Client Connection Failed: " + reason.getErrorMessage())
		self.callback(False)
	
	def clientConnectionLost(self, connector, reason):
		log.msg("Connection lost: " + reason.getErrorMessage())

class NATService(object):
	def __init__(self, clientObject):
		self.service = EchoService()
		self.clientObject = clientObject
	
	
	def run(self, regionEnd):
		regionStart = 9000
		log.msg("[NAT] Check Start")
		d = Deferred()
		d.addCallback(self.allEstablished)
		self.tcount = 0
		self.done = False
		self.ports2 = None
		if regionStart != regionEnd and regionEnd >= 9000:
			self.ports2 = [8002, 8003, 8004, regionStart, regionEnd]
		else:
			self.ports2 = [8002, 8003, 8004, regionStart]
		self.ports = []
		for port in self.ports2:
			hasProcessRunning = False
			for name in self.clientObject.processes:
				process = self.clientObject.processes[name]
				if process.consolePort == port + 10000:
					hasProcessRunning = True
				if process.consolePort == 18000:
					if port == 8002 or port == 8003 or port == 8004:
						hasProcessRunning = True
			if not hasProcessRunning:
				self.ports += [port]
		self.count = len(self.ports)
		self.service.start(d, self.count, self.ports)
	
	def allEstablished(self, ignored):
		log.msg("[NAT] All servers listening")
		exthost = self.clientObject.externalhost
		factory = EchoClientFactory(self.resultReceived)
		for port in self.ports:
			log.msg("[NAT] Starting Echo Client on port " + str(port))
			reactor.connectTCP(exthost, port, factory)
	
	def resultReceived(self, result):
		if not self.done:
			log.msg("[NAT] Received Status: " + str(result))
			if result:
				self.tcount += 1
				if self.tcount == self.count:
					self.done = True
					self.success()
			else:
				self.done = True
				self.failure()
	
	def success(self):
		self.service.close()
		self.continuenat()

	def failure(self):
		delta = DeltaUser(self.clientObject.localUUID)
		delta.NATStatus = False
		self.clientObject.protocol.writeRequest(delta)
		self.service.close()
	
	def continuenat(self):
		processes = self.clientObject.processes
		if len(processes) == 0:
			delta = DeltaUser(self.clientObject.localUUID)
			delta.NATStatus = True
			self.clientObject.protocol.writeRequest(delta)
			return
			
		log.msg("[NAT] Testing HTTP consoles")
		self.proccount = 0
		self.postrescount = 0
		self.procdone = False
		for name in processes:
			log.msg("[NAT] Testing HTTP console for process " + name)
			self.proccount += 1
			process = processes[name]
			process.sendCommand("", {}, self.postresponse)
		reactor.callLater(5, self.timeout)
	
	def postresponse(self, response):
		self.postrescount += 1
		log.msg("[NAT] Received HTTP Response. Count: " + str(self.postrescount))
		if self.postrescount == self.proccount:
			self.procdone = True
			delta = DeltaUser(self.clientObject.localUUID)
			delta.NATStatus = True
			self.clientObject.protocol.writeRequest(delta)
	
	def timeout(self):
		if not self.procdone:
			delta = DeltaUser(self.clientObject.localUUID)
			delta.NATStatus = False
			self.clientObject.protocol.writeRequest(delta)
