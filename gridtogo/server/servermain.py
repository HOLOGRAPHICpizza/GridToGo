from twisted.internet import protocol, reactor
from twisted.protocols import basic
import authentication
import configuration
import database
from gridtogo.shared import serialization, networkobjects
from gridtogo.shared.networkobjects import *

PRINT_PACKETS = True

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
			print("Listening on port %d." % config.port)
			GridToGoServer.reactor.run()
		except AttributeError:
			pass
		return GridToGoServer.exitcode

class Grid(object):
	def __init__(self, name, users):
		self.name = name

		# This is a dictionary mapping UUIDs to User objects
		self.users = users

		# This is a list of connected protocols
		self.protocols = []

	def applyUserDelta(self, user):
		self.users[user.UUID].applyDelta(user)
		self.writeResponseToAll(user)

	def writeResponseToAll(self, response):
		for p in self.protocols:
			p.writeResponse(response)

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

		# This is a reference to the grid object this protocol belongs to
		self.grid = None
		self.user = None

	def connectionMade(self):
		pass

	def lineReceived(self, line):
		try:
			#TODO: Perhaps in the future we should make (de)serialization operations asynchronous,
			# not sure if this is worth the effort/overhead or not.
			# The same can be said for all database lookups.
			request = self.serializer.deserialize(line)
			if PRINT_PACKETS:
				print("IN : %s | %s" % (request.__class__.__name__, line))

			if not self.user:
				if isinstance(request, LoginRequest):
					response, userAccount = self.authenticator.authenticateUser(request)
					self.writeResponse(response)

					if isinstance(response, LoginSuccess):
						print("%s %s has logged in to grid %s." % (request.firstName, request.lastName, request.grid))

						# Load this user's grid if we haven't already
						if not request.grid in self.grids:
							print("Loading grid %s from database..." % request.grid)
							self.grids[request.grid] = Grid(request.grid, self.database.getGridUsers(request.grid))
						self.grid = self.grids[request.grid]

						# Join the user to this grid if they are not a member
						#TODO: Implement "restricted" grids that have an access list
						self.user = self.grid.users.get(userAccount.UUID)
						if not self.user:
							print("Joining user to grid %s...", self.grid.name)
							# Create a new user. If first user, give mod and host.
							self.user = User(userAccount.UUID)
							self.user.firstName = userAccount.firstName
							self.user.lastName = userAccount.lastName
							# The user will be set online when we apply the delta below, not here
							self.user.online = False
							self.user.moderator = (len(self.grid.users) < 1)
							self.user.gridHost = self.user.moderator
							self.grid.users[self.user.UUID] = self.user
							self.database.storeGridAssociation(self.user, request.grid)

						# send the client all the User objects in the grid
						for id in self.grid.users:
							self.writeResponse(self.grid.users[id])

						# register this user's connection in our list
						self.grid.protocols.append(self)

						# mark this user online with a delta object
						delta = User(self.user.UUID)
						delta.online = True
						self.grid.applyUserDelta(delta)

				elif isinstance(request, ResetPasswordRequest):
					response = self.authenticator.resetPassword(request)
					self.writeResponse(response)

				elif isinstance(request, CreateUserRequest):
					response = self.authenticator.createUser(request)
					self.writeResponse(response)

			else:
				# User is authenticated.
				pass

		except serialization.InvalidSerializedDataException:
			self.transport.write("Stop sending me bad data! >:|\r\n")
			self.transport.loseConnection()

	def writeResponse(self, response):
		line = self.serializer.serialize(response)
		if PRINT_PACKETS:
			print("OUT: %s | %s" % (response.__class__.__name__, line))
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
