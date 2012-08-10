from twisted.internet import gtk3reactor
gtk3reactor.install()

from gi.repository import Gtk
import sys
from twisted.internet import protocol, reactor, endpoints, defer
from twisted.protocols import basic
from twisted.python import log
from gridtogo.shared.nat import NATService
from gridtogo.shared import serialization, networkobjects
from gridtogo.shared.networkobjects import *
from ui.windows import *

PRINT_PACKETS = False

class GridToGoClient(object):
	"""
	One instance of this class should exist in our application.
	This holds shared state for the whole program.
	"""
	def __init__(self, projectRoot):
		self.projectRoot = projectRoot
		self.factory = GTGClientFactory(self)

		self.endpoint = None
		self.attempt = None
		self.protocol = None

		self.windowFactory = None
		self.loginHandler = None
		self.createUserWindowHandler = None
		self.spinner = None
		self.mainWindowHandler = None
		self.CreateRegionWindowHandler = None
		self.AboutWindowHandler = None

		# dict mapping process names to process protocols
		self.processes = {}

		# dict mapping UUIDs to User objects
		# The cleint's local list of all grid users
		self.users = {}
		self.regions = {}
		# This is how we remember who we are.
		self.localUUID = None

		self.email = None
		self.password = None

		self.maxregionport = 8999
		
		self.externalhost = None

		# Ghetto flag involved in control of the form's

		self.dieing = False

		# list of functions to call when we get a connection
		# passes a reference to a Protocol to each
		self.callOnConnected = []
		#TODO: implement a callOnConnectionFailed list - MAYBE, IF NECESSARY

		log.startLogging(sys.stdout)

	def getLocalUser(self):
		return self.users[self.localUUID]

	def run(self):
		self.windowFactory = WindowFactory(self)
		self.loginHandler = self.windowFactory.buildWindow('loginWindow', LoginWindowHandler)
		self.loginHandler.window.show_all()

		reactor.run()
	
	def addUser(self, user):
		self.users[user.UUID] = user
		if self.mainWindowHandler:
			self.mainWindowHandler.updateUser(user)

	def updateUser(self, user):
		if self.users.get(user.UUID):
			self.users[user.UUID].applyDelta(user)
			if self.mainWindowHandler:
				self.mainWindowHandler.updateUser(self.users[user.UUID])
		else:
			log.err("Received DeltaUser for non existent User. Ignoring")
	
	def addRegion(self, region):
		self.regions[region.regionName] = region
		if self.mainWindowHandler:
			self.mainWindowHandler.regionList.updateRegion(region)
	
	def updateRegion(self, region):
		if self.regions.get(region.regionName):
			self.regions[region.regionName].applyDelta(region)
			if self.mainWindowHandler:
				self.mainWindowHandler.regionList.updateUser(self.regions[region.regionName])
		else:
			log.err("Received DeltaRegion for non existent Region. Ignoring")

	def attemptConnection(self, spinnerParent, host, port, timeout):
		if self.protocol:
			# assume we are already connected and call onConnected again
			self.onConnected(self.protocol)
		if self.attempt:
			log.msg("connection attempt already in progress!")
			return

		self.spinner = SpinnerPopup(spinnerParent, 'Connecting...')
		self.spinner.show_all()

		self.endpoint = endpoints.TCP4ClientEndpoint(reactor, host, port, timeout)
		self.attempt = self.endpoint.connect(self.factory)
		self.attempt.addCallback(self.onConnected)
		self.attempt.addErrback(self.onConnectionFailed)
		self.attempt.window = spinnerParent

	def onConnected(self, protocol):
		self.spinner.destroy()
		self.attempt = None
		self.protocol = protocol
		for f in self.callOnConnected:
			if callable(f):
				f(protocol)

	def onConnectionFailed(self, failure):
		self.spinner.destroy()
		showModalDialog(self.attempt.window, Gtk.MessageType.ERROR, failure.value)
		self.attempt = None
		self.endpoint = None

	def stop(self):
		#TODO: Get the program to stop in a smooth fashion
		if self.loginHandler and self.loginHandler.window:
			self.loginHandler.window.destroy()
		if self.createUserWindowHandler:
			self.createUserWindowHandler.destroy()
		if self.mainWindowHandler and self.mainWindowHandler.window:
			self.mainWindowHandler.window.destroy()
		if self.CreateRegionWindowHandler:
			self.CreateRegionWindowHandler.destroy()
		if self.AboutWindowHandler:
			self.AboutWindowHandler.destroy()

		# Kill any sub-processes that are running
		for name in self.processes:
			self.processes[name].transport.signalProcess('KILL')

		#TODO: Check if reactor is running before calling stop
		reactor.stop()

	def robustEnded(self, processName, reason):
		del self.processes[processName]

		self.mainWindowHandler.setStatus('Grid Server (ROBUST) stopped.')

		delta = DeltaUser(self.localUUID)
		delta.gridHostActive = False
		self.protocol.writeRequest(delta)

	def processRobustOutput(self, processName, line):
		# We need to make sure all the UGAIM services come up:
		#   Asset Service
		#   Grid Service
		print(line)

	def processSimOutput(self, processName, line):
		print(line)

class GTGClientProtocol(basic.LineReceiver):
	def __init__(self, clientObject, serializer):
		# Alias for convenience
		self.serializer = serializer
		self.clientObject = clientObject
		self.nat = NATService(clientObject)

	def lineReceived(self, line):
		try:
			#TODO: Perhaps in the future we should make (de)serialization operations asynchronous,
			# not sure if this is worth the effort/overhead or not.
			response = self.serializer.deserialize(line)

			if PRINT_PACKETS:
				log.msg("IN : %s | %s" % (response.__class__.__name__, line))

			# User Objects
			if isinstance(response, User) and self.clientObject.mainWindowHandler:
				self.clientObject.addUser(response)

			if isinstance(response, DeltaUser) and self.clientObject.mainWindowHandler:
				self.clientObject.updateUser(response)

			# Region Objects
			if isinstance(response, Region) and self.clientObject.mainWindowHandler:
				self.clientObject.addRegion(response)

			if isinstance(response, DeltaRegion) and self.clientObject.mainWindowHandler:
				self.clientObject.updateRegion(response)

			elif isinstance(response, NATCheckResponse) and self.clientObject.mainWindowHandler:
				log.msg("[NAT] Status = " + str(response.status))
				delta = DeltaUser(self.clientObject.localUUID)
				delta.NATStatus = response.status
				self.writeRequest(delta)
				self.nat.close()

			# Login Stuff
			elif isinstance(response, LoginResponse) and self.clientObject.loginHandler:
				if isinstance(response, LoginSuccess):
					self.clientObject.localUUID = response.UUID
					self.clientObject.localGrid = response.grid
					self.clientObject.email = response.email
					self.clientObject.externalhost = response.externalhost

					self.clientObject.mainWindowHandler = \
						self.clientObject.windowFactory.buildWindow("mainWindow", MainWindowHandler)
					self.clientObject.mainWindowHandler.window.show_all()
					self.clientObject.mainWindowHandler.setStatus('Logged in to coordination server.')

					self.clientObject.loginHandler.window.destroy()
					self.clientObject.loginHandler = None

					self.nat.run(self.clientObject.maxregionport)
				else:
					showModalDialog(
						self.clientObject.loginHandler.window,
						Gtk.MessageType.ERROR,
						response.message)

			# Create User Stuff
			elif isinstance(response, CreateUserResponse) and self.clientObject.createUserWindowHandler:
				if isinstance(response, CreateUserSuccess):
					self.clientObject.createUserWindowHandler.onCreateUserSuccess()
					self.clientObject.createUserWindowHandler.window.destroy()
					self.clientObject.createUserWindowHandler = None
				else:
					showModalDialog(
						self.clientObject.createUserWindowHandler.window,
						Gtk.MessageType.ERROR,
						response.message)

		except serialization.InvalidSerializedDataException:
			log.msg("Server sent bad data.")
			self.transport.loseConnection()

	def connectionLost(self, reason):
		if not self.clientObject.dieing:
			showModalDialog(None, Gtk.MessageType.ERROR, 'Connection lost!')
			self.clientObject.dieing = True
			self.clientObject.stop()

	def writeRequest(self, request):
		line = self.serializer.serialize(request)
		if PRINT_PACKETS:
			log.msg("OUT: %s | %s" % (request.__class__.__name__, line))
		self.transport.write(line + "\r\n")

class GTGClientFactory(protocol.ClientFactory):
	def __init__(self, clientObject):
		self.serializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))
		self.clientObject = clientObject

	def buildProtocol(self, addr):
		return GTGClientProtocol(self.clientObject, self.serializer)
