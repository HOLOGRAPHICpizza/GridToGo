from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol
from twisted.python import log

class EchoProtocol(Protocol):
	def __init__(self, factory, port):
		self.factory = factory
		self.port = port
	
	def connectionMade(self):
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
		self.builder.protocols += [protocol]
		return protocol

class EchoFactoryBuilder(object):
	def __init__(self):
		self.protocols = []

	def buildFactory(self, port):
		return EchoFactory(self, port)

class EchoService(object):
	def __init__(self):
		log.msg("[NAT] Creating Echo Service")
		self.builder = EchoFactoryBuilder()
	
	def listenOn(self, port):
		endpoint = TCP4ServerEndpoint(reactor, port)
		endpoint.listen(self.builder.buildFactory(port))
	
	def close(self):
		log.msg("[NAT] Closing Echo Service")
		for protocol in self.builder.protocols:
			protocol.close()
