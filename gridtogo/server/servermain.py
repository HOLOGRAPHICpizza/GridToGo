from twisted.internet import protocol, reactor
from twisted.protocols import basic
from twisted.application import service
import database
import authentication
from gridtogo.shared import serialization, networkobjects
from gridtogo.shared.networkobjects import *

class GridToGoServer(object):
	def __init__(self, port):
		self.port = port

	def run(self):
#		testRequest = LoginRequest('Michael', 'Craft', 'testpass', 'testgrid')
#		testSerializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))
#		print(testSerializer.serialize(testRequest))

		reactor.listenTCP(self.port, GTGFactory())
		reactor.run()


class GTGProtocol(basic.LineReceiver):
	"""
	Stateful communication with clients through a one-line-per-request serialization format.
	Any serialization can be used, default implementation is JSON.
	One of these is created for each client connection.
	"""
	def __init__(self, serializer, authenticator):
		# Aliases for convenience
		self.serializer = serializer
		self.authenticator = authenticator

	def connectionMade(self):
		pass

	def lineReceived(self, line):
		try:
			request = self.serializer.deserialize(line)

			if isinstance(request, LoginRequest):
				response = self.authenticator.authenticateUser(request)
				self.transport.write(self.serializer.serialize(response)+"\r\n")

		except serialization.InvalidSerializedDataException:
			self.transport.write("Stop sending me bad data! >:|\r\n")
			self.transport.loseConnection()

class GTGFactory(protocol.ServerFactory):
	def __init__(self):
		self.database = database.IDatabase(database.DummyDatabase())
		self.authenticator = authentication.Authenticator(self.database)
		self.serializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))

	def buildProtocol(self, addr):
		return GTGProtocol(self.serializer, self.authenticator)

#TODO: Use service and twistd to daemonize
#class GTGService(service.Service):
#	"""
#	Creates GTGFactory instances.
#	This is a service in the actual UNIX sense, this is the server proper which serves the protocol.
#	It can be run on any port by the reactor.
#	"""
#	def __init__(self):
#		self.database = database.IDatabase(database.DummyDatabase())
#		self.authenticator = authentication.Authenticator(self.database)
#		self.serializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))
#
#	def getGTGFactory(self):
#		f = protocol.ServerFactory()
#		f.protocol = GTGProtocol
#		f.serializer = self.serializer
#		f.authenticator = self.authenticator
#		return f
