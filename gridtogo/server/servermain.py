from twisted.internet import protocol, reactor
from twisted.protocols import basic
from twisted.application import service
import authentication
import configuration
import database
from gridtogo.shared import serialization, networkobjects
from gridtogo.shared.networkobjects import *

class GridToGoServer(object):
	"""Ony one object of this class should exist per python interpreter."""
	def __init__(self):
		GridToGoServer.exitcode = 0
		GridToGoServer.reactor = reactor

	def run(self):
		#testRequest = LoginRequest('Michael', 'Craft', 'testpass', 'testgrid')
		#testSerializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))
		#print(testSerializer.serialize(testRequest))
	
		config = configuration.ConfigurationLoader().load()

		try:
			#TODO: Use SSL so we're not sending passwords in plaintext anymore
			GridToGoServer.reactor.listenTCP(config.port, GTGFactory(config))
			GridToGoServer.reactor.run()
		except AttributeError:
			pass
		return GridToGoServer.exitcode


# Protocol example of successful login
# Client        -   Server
#
# LoginRequest  >
#               <   LoginResponse
#               <   Send all entities currently relevant
#               <   Client is now subscribed and will be sent updates
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

		self.authenticated = False

	def connectionMade(self):
		pass

	def lineReceived(self, line):
		try:
			#TODO: Perhaps in the future we should make (de)serialization operations asynchronous,
			# not sure if this is worth the effort/overhead or not.
			# The same can be said for all database lookups.
			request = self.serializer.deserialize(line)

			if not self.authenticated:
				if isinstance(request, LoginRequest):
					response = self.authenticator.authenticateUser(request)
					if isinstance(response, LoginSuccess):
						self.authenticated = True
					self._writeResponse(response)

				elif isinstance(request, CreateUserRequest):
					response = self.authenticator.createUser(request)
					self._writeResponse(response)

				elif isinstance(request, ResetPasswordRequest):
					pass

			else:
				# User is authenticated.
				pass

		except serialization.InvalidSerializedDataException:
			self.transport.write("Stop sending me bad data! >:|\r\n")
			self.transport.loseConnection()

	def _writeResponse(self, response):
		self.transport.write(self.serializer.serialize(response)+"\r\n")

class GTGFactory(protocol.ServerFactory):
	def __init__(self, config):
		try:
			#TODO: Call the database's close() method on program exit.
			self.database = database.IDatabase(database.SQLiteDatabase(config.dbfile))
		except database.DatabaseException as e:
			# Believe it or not, this is our standard failure procedure.
			GridToGoServer.exitcode = 1
			del GridToGoServer.reactor
			raise e

		self.authenticator = authentication.Authenticator(self.database)
		self.serializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))

	def buildProtocol(self, addr):
		return GTGProtocol(self.serializer, self.authenticator)

#TODO: Use service and twistd to daemonize
#      Or perhaps not, there are drawbacks with command args and return codes
#
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
