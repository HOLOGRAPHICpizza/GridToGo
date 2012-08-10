import socket
import string
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, ClientFactory, Factory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
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
		self.ports2 = None
		if regionStart != regionEnd and regionEnd >= 9000:
			self.ports2 = [8002, 8003, 8004, regionStart, regionEnd]
		else:
			self.ports2 = [8002, 8003, 8004, regionStart]
		self.ports = []
		self.processports = []
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
			else:
				if port == 8002:
					self.processports += [18000]
				elif port != 8003 and port != 8004: # We only want ROBUST once.
					self.processports += [port + 10000]
		self.count = len(self.ports)
		self.service.start(d, self.count, self.ports)
	
	def allEstablished(self, ignored):
		log.msg("[NAT] All servers listening")
		self.clientObject.protocol.writeRequest(NATCheckRequest(self.ports, self.processports))
	
	def close(self):
		self.service.close()

# TODO Test process ports here.
class NATClientService(object):
	def __init__(self, protocol):
		self.protocol = protocol

	def run(self, ports, processports=[]):
		self.host = self.protocol.transport.getPeer().host
		self.ports = ports
		self.processports = processports
		self.tcount = 0
		self.count = len(ports)
		self.done = False
		factory = EchoClientFactory(self.resultReceived)
		for port in self.ports:
			log.msg("[NAT] Starting Echo Client at: " + self.host + ":" + str(port))
			reactor.connectTCP(self.host, port, factory)
	
	def resultReceived(self, result):
		if not self.done:
			log.msg("[NAT] Received Status: " + str(result))
			if result:
				self.tcount += 1
				if self.tcount == self.count:
					self.done = True
					self.checkprocesses()
			else:
				self.done = True
				self.failure()
	
	def success(self):
		self.protocol.writeResponse(NATCheckResponse(True))

	def failure(self):
		self.protocol.writeResponse(NATCheckResponse(False))
	
	def checkprocesses(self):
		self.pdone = False
		self.ptotalcount = len(self.processports)
		if self.ptotalcount < 1:
			self.success()
			return
		self.pcount = 0
		for port in self.processports:
			def request(response):
				self.pcount += 1
				if self.pcount == self.ptotalcount:
					self.pdone = True
					self.success()

			def err(response):
				log.msg("[NAT] Received Error in making a process connection. Port = " + str(port) + ". Reason = " + str(response))
				if not self.pdone:
					self.pdone = True
					self.failure()

			def timeout():
				if not self.pdone:
					self.failure()

			agent = Agent(reactor)
			d = agent.request(
				'GET',
				'http://' + self.host + ':' + str(port),
				Headers({'User-Agent': ['GridToGo Server']}),
				None)
			d.addCallback(request)
			d.addErrback(err)
			reactor.callLater(5, timeout)

class LoopbackEchoFactory(Factory):
	def __init__(self, port):
		self.port = port

	def buildProtocol(self, addr):
		return EchoProtocol(self, self.port)

class LoopbackService(object):
	def __init__(self, clientObject, exthost):
		self.clientObject = clientObject
		self.exthost = exthost
		self.factory = EchoClientFactory(self.result)
	
	def run(self):
		log.msg("[NAT] Listening on port " + str(8001))
		endpoint = TCP4ServerEndpoint(reactor, 8001)
		d = endpoint.listen(LoopbackEchoFactory(8001))
		d.addCallback(self.started)
	
	def started(self, connection):
		log.msg("[NAT] Connecting to Loopback: " + self.exthost)
		reactor.connectTCP(self.exthost, 8001, self.factory)
		self.connection = connection
	
	def result(self, status):
		log.msg("[NAT] Loopback Status = " + str(status))
		delta = DeltaUser(self.clientObject.localUUID)
		delta.NATStatus = status
		self.clientObject.protocol.writeRequest(delta)
		self.connection.stopListening()
