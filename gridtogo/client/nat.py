from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol
from twisted.python import log

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
	def __init__(self, deferred, finalCount):
		log.msg("[NAT] Creating Echo Service")
		self.builder = EchoFactoryBuilder()
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
