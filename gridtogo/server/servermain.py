from twisted.internet import protocol, reactor
from twisted.protocols import basic
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
	def __init__(self, serializer, database, authenticator, grids):
		# Aliases for convenience
		self.serializer = serializer
		self.database = database
		self.authenticator = authenticator
		self.grids = grids

		self.authenticated = False

	def connectionMade(self):
		pass

	def lineReceived(self, line):

		#print("IN : " + line)

		try:
			#TODO: Perhaps in the future we should make (de)serialization operations asynchronous,
			# not sure if this is worth the effort/overhead or not.
			# The same can be said for all database lookups.
			request = self.serializer.deserialize(line)

			if not self.authenticated:
				if isinstance(request, LoginRequest):
					response, userAccount = self.authenticator.authenticateUser(request)
					self._writeResponse(response)

					if isinstance(response, LoginSuccess):
						self.authenticated = True

						# Load this user's grid if we haven't already
						if not request.grid in self.grids:
							self.grids[request.grid] = Grid(request.grid, self.database.getGridUsers(request.grid))
						grid = self.grids[request.grid]

						# Join the user to this grid if they are not a member
						#TODO: Implement "restricted" grids that have an access list
						user = grid.users.get(userAccount.UUID)
						if not user:
							# Create a new user. If first user, give mod and host.
							user = User(userAccount.UUID)
							user.firstName = userAccount.firstName
							user.lastName = userAccount.lastName
							user.online = True
							user.moderator = (len(grid.users) < 1)
							user.gridHost = user.moderator
							grid.users[user.UUID] = user
							self.database.storeGridAssociation(user, request.grid)
							print("added user to grid")

						# send the client all the User objects in the grid
						for id in grid.users:
							u = grid.users[id]
							self._writeResponse(u)



				elif isinstance(request, ResetPasswordRequest):
					response = self.authenticator.resetPassword(request)
					self._writeResponse(response)

				elif isinstance(request, CreateUserRequest):
					response = self.authenticator.createUser(request)
					self._writeResponse(response)

			else:
				# User is authenticated.
				pass

		except serialization.InvalidSerializedDataException:
			self.transport.write("Stop sending me bad data! >:|\r\n")
			self.transport.loseConnection()

	def _writeResponse(self, response):
		line = self.serializer.serialize(response)
		#print("OUT: " + line)
		self.transport.write(line + "\r\n")

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

		# A dictionary of Grid objects
		self.grids = {}

	def buildProtocol(self, addr):
		return GTGProtocol(self.serializer, self.database, self.authenticator, self.grids)

class Grid(object):

	def __init__(self, name, users):
		self.name = name
		self.users = users
