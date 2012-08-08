import sys
from twisted.internet import protocol, reactor
from twisted.protocols import basic
from twisted.python import log
import authentication
import configuration
import database
from gridtogo.shared import serialization, networkobjects
from gridtogo.shared.networkobjects import *

PRINT_PACKETS = False

class GridToGoServer(object):
	"""Ony one object of this class should exist per python interpreter."""
	def __init__(self):
		GridToGoServer.exitcode = 0
		GridToGoServer.reactor = reactor
		log.startLogging(sys.stdout)

	def run(self):
		#testRequest = LoginRequest('Michael', 'Craft', 'testpass', 'testgrid')
		#testSerializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))
		#log.msg(testSerializer.serialize(testRequest))
	
		config = configuration.ConfigurationLoader().load()

		try:
			#TODO: Use SSL so we're not sending passwords in plaintext anymore
			GridToGoServer.reactor.listenTCP(config.port, GTGFactory(config))
			#log.msg("Listening on port %d." % config.port)
			GridToGoServer.reactor.run()
		except AttributeError:
			pass
		return GridToGoServer.exitcode

class Grid(object):
	def __init__(self, name, users, regions):
		self.name = name

		# This is a dictionary mapping UUIDs to User objects
		self.users = users

		# This is a dictionary mapping names to Region objects
		self.regions = regions

		# maps UUIDs to Protocol objects
		self.protocols = {}

	def applyUserDelta(self, userdelta):
		self.users[userdelta.UUID].applyDelta(userdelta)
		self.writeResponseToAll(userdelta)

	def writeResponseToAll(self, response):
		for uuid in self.protocols:
			self.protocols[uuid].writeResponse(response)

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

	def lineReceived(self, line):
		try:
			#TODO: Perhaps in the future we should make (de)serialization operations asynchronous,
			# not sure if this is worth the effort/overhead or not.
			# The same can be said for all database lookups.
			request = self.serializer.deserialize(line)
			if PRINT_PACKETS:
				log.msg("IN : %s | %s" % (request.__class__.__name__, line))

			if not self.user:
				if isinstance(request, LoginRequest):
					response, userAccount = self.authenticator.authenticateUser(request)
					response.externalhost = self.transport.getPeer().host
					self.writeResponse(response)

					if isinstance(response, LoginSuccess):
						log.msg("%s %s has logged in to grid %s." % (request.firstName, request.lastName, request.grid))


						# Load this user's grid if we haven't already
						if not request.grid in self.grids:
							log.msg("Loading grid %s from database..." % request.grid)
							self.grids[request.grid] = Grid(request.grid, self.database.getGridUsers(request.grid), self.database.getGridRegions(request.grid))
						self.grid = self.grids[request.grid]

						# Join the user to this grid if they are not a member
						#TODO: Implement "restricted" grids that have an access list
						#log.msg("SET USER 1")
						self.user = self.grid.users.get(userAccount.UUID)
						if not self.user:
							log.msg("Joining user to grid %s..." % self.grid.name)
							# Create a new user. If first user, give mod and host.
							#log.msg("SET USER 2")
							self.user = User(userAccount.UUID,
								userAccount.firstName, userAccount.lastName,
								True, False, (len(self.grid.users) < 1),
								(len(self.grid.users) < 1), False)
							self.grid.users[self.user.UUID] = self.user
							self.database.storeGridAssociation(self.user, request.grid)

							# broadcast this new user to connected clients
							self.grid.writeResponseToAll(self.user)

						# Duplicate instance checking
						#TODO: Kick old user off with a message instead of this hacky refusal
						if self.grid.protocols.get(self.user.UUID):
							self.transport.write('No multiple instances! >:O')
							self.transport.loseConnection()

						# send the client all the User objects in the grid
						for id in self.grid.users:
							self.writeResponse(self.grid.users[id])

						# send the client all the Region objects in the grid
						for n in self.grid.regions:
							self.writeResponse(self.grid.regions[n])

						# register this user's connection in our list
						self.grid.protocols[self.user.UUID] = self

						# mark this user online with a delta object
						delta = DeltaUser(self.user.UUID)
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

				if isinstance(request, DeltaUser):
					delta = None

					# moderators can change anything
					if self.user.moderator:
						delta = request

					# Users talking about themselves may change certain attributes
					elif request.UUID == self.user.UUID:
						delta = DeltaUser(request.UUID)

						# Online Status
						if hasattr(request, 'online'):
							delta.online = request.online

						# Surrendering GridHost
						if hasattr(request, 'gridHost') and self.user.gridHost:
							delta.gridHost = request.gridHost

						# gridHostActive
						if hasattr(request, 'gridHostActive') and self.user.gridHost:
							delta.gridHostActive = request.gridHostActive

					else:
						# This user has no permission
						return

					if delta:
						# Apply server-side delta
						self.grid.applyUserDelta(delta)

						# Replicate changes
						self.grid.writeResponseToAll(delta)

						# Save to database if necessary
						if hasattr(delta, 'gridHost') or hasattr(delta, 'moderator'):
							self.database.storeGridAssociation(delta, self.grid.name)

				elif isinstance(request, CreateRegionRequest):
					log.msg("Creating new region on grid %s: %s" % (request.gridName, request.regionName))
					self.database.createRegion(request.gridName, request.regionName, request.location, request.uuid)
					region = Region(request.regionName, request.location, None, [self.user.UUID])
					self.grid.regions[region.regionName] = region
					self.grid.writeResponseToAll(region)

		except serialization.InvalidSerializedDataException:
			self.transport.write("Stop sending me bad data! >:|\r\n")
			self.transport.loseConnection()

	def connectionLost(self, reason):
		if self.user:
			if self.grid.protocols.get(self.user.UUID):
				del self.grid.protocols[self.user.UUID]
			delta = DeltaUser(self.user.UUID)
			delta.online = False
			delta.NATStatus = False
			delta.gridHostActive = False
			self.grid.applyUserDelta(delta)

			print("%s %s has disconnected." % (self.user.firstName, self.user.lastName))

	def writeResponse(self, response):
		line = self.serializer.serialize(response)
		if PRINT_PACKETS:
			log.msg("OUT: %s | %s" % (response.__class__.__name__, line))
		self.transport.write(line + "\r\n")

class GTGFactory(protocol.ServerFactory):
	def __init__(self, config):
		try:
			#TODO: Call the database's close() method on program exit.
			if config.dbtype == "sqlite":
				log.msg("Connecting to SQLite")
				self.database = database.IDatabase(database.SQLiteDatabase())
			elif config.dbtype == "mongo":
				log.msg("Connecting to Mongo")
				self.database = database.IDatabase(database.MongoDatabase())
			else:
				log.err("Bad Database Type. Probably going to crash and burn")
			self.database.connect(config)
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
