import socket
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, ClientFactory, Factory
from twisted.protocols.basic import LineReceiver
from twisted.python import log

from gridtogo.shared.networkobjects import *

class EchoProtocol(Protocol):
	def __init__(self, factory, port):
		self.factory = factory
		self.port = port
	
	def connectionMade(self):
		self.factory.builder.service.connectionCount += 1
		self.factory.builder.service.checkCount()
		log.msg("[NAT] Established Connection on port " + str(port))
	
	def connectionLost(self):
		log.msg("[NAT] Lost Connection on port " + str(port) + ". Reason: " + str(reason))

	def close(self):
		self.transport.loseConnection()
	
	def dataReceived(self, data):
		self.transport.write(data)

class EchoFactory(Factory):
	def __init__(self, builder, port):
		self.builder = builder
		self.port = port

	def buildProtocol(self, addr):
		protocol = EchoProtocol(self.port)
		self.builder.service.protocols += [protocol]
		return protocol

class EchoFactoryBuilder(object):
	def __init__(self, service):
		self.service = service

	def buildFactory(self, port):
		return EchoFactory(self, port)

class EchoService(object):
	def __init__(self):
		log.msg("[NAT] Creating Echo Service")
	
	def start(self, deferred, finalCount):
		log.msg("[NAT] Starting Echo Service")
		self.builder = EchoFactoryBuilder(self)
		self.protocols = []
		self.connectionCount = 0
		self.deffered = deferred
		self.finalCount = finalCount
	
	def listenOn(self, port):
		endpoint = TCP4ServerEndpoint(reactor, port)
		endpoint.listen(self.builder.buildFactory(port))
	
	def close(self):
		log.msg("[NAT] Closing Echo Service")
		for protocol in self.builder.protocols:
			protocol.close()
	
	def checkCount(self):
		if self.connectionCount == self.finalCount:
			deferred.callback(self)

class EchoClient(LineReceiver):
	def __init__(self, deferred):
		self.code = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(16))
		self.deferred = deferred
		self.timedout = False

	def connectionMade(self):
		self.sendLine(self.code)
		reactor.callLater(5, timeout)
	
	def lineReceived(self, line):
		if not self.timedout:
			if(line == self.code):
				self.deferred.callback(True)
			else:
				self.deferred.callback(False)
		self.close()
	
	def timeout(self):
		self.deferred.classback(False)
		self.close()

class EchoClientFactory(ClientFactory):
	protocol = EchoClient

	def __init__(self, deferred):
		self.deferred = deferred

	def buildProtocol(self, addr):
		return EchoClient(deferred)

	def clientConnectionFailed(self, connector, reason):
		log.msg("NAT Echo Client Connection Failed: " + reason.getErrorMessage())
		self.deferred.callback(False)
	
	def clientConnectionLost(self, connector, reason):
		log.msg("Connection lost: " + reason.getErrorMessage())

class NATService(object):
	def __init__(self, clientObject):
		self.service = EchoService()
		self.clientObject = clientObject
	
	def handle(self, request):
		if isinstance(request, NATCheckStartRequest):
			self.run(request.regionStart, request.regionEnd)
	
	def run(self, regionStart, regionEnd):
		d = Deferred()
		d.addCallback(self.allEstablished)
		self.count = 4 + regionEnd - regionStart
		self.tcount = 0
		self.done = False
		self.service.start(d, self.count)
	
	def allEstablished(self, ignored):
		exthost = socket.gethostbyaddr(socket.gethostname())[0]
	
	def resultReceived(self, result):
		if not self.done:
			if result:
				self.tcount += 1
				if self.tcount == self.count:
					self.done = True
					self.success()
			else:
				self.done = True
				self.failure()
	
	def success(self):
		delta = DeltaUser(self.clientObject.localUUID)
		delta.NATStatus = True
		self.clientObject.writeRequest(delta)
		self.close()

	def failure(self):
		delta = DeltaUser(self.clientObject.localUUID)
		delta.NATStatus = False
		self.clientObject.writeRequest(delta)
		self.close()
