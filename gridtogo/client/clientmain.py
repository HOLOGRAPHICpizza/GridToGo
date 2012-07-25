from twisted.internet import gtk3reactor
gtk3reactor.install()

from gi.repository import Gtk
import sys
from twisted.internet import protocol, reactor, endpoints, defer
from twisted.protocols import basic
from twisted.python import log
from gridtogo.shared import serialization, networkobjects
from gridtogo.shared.networkobjects import *
from ui.windows import *

PRINT_PACKETS = True

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
		self.createRegionWindowHandler = None

		# Ghetto flag involved in
		self.dieing = False

		# list of functions to call when we get a connection
		# passes a reference to a Protocol to each
		self.callOnConnected = []
		#TODO: implement a callOnConnectionFailed list - MAYBE, IF NECESSARY

		log.startLogging(sys.stdout)

	def run(self):
		self.windowFactory = WindowFactory(self)
		self.loginHandler = self.windowFactory.buildWindow('loginWindow', LoginWindowHandler)
		self.loginHandler.window.show_all()

		reactor.run()

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
		#TODO: Get this damn thing to stop in a graceful manner
		if self.loginHandler and self.loginHandler.window:
			self.loginHandler.window.destroy()
		if self.createUserWindowHandler:
			self.createUserWindowHandler.destroy()
		if self.createRegionWindowHandler:
			self.createRegionWindowHandler.destroy()
		if self.mainWindowHandler and self.mainWindowHandler.window:
			self.mainWindowHandler.window.destroy()

		#TODO: Check if reactor is running before calling stop
		reactor.stop()

class GTGClientProtocol(basic.LineReceiver):
	def __init__(self, clientObject, serializer):
		# Alias for convenience
		self.serializer = serializer
		self.clientObject = clientObject

	def lineReceived(self, line):
		try:
			#TODO: Perhaps in the future we should make (de)serialization operations asynchronous,
			# not sure if this is worth the effort/overhead or not.
			response = self.serializer.deserialize(line)

			if PRINT_PACKETS:
				log.msg("IN : %s | %s" % (response.__class__.__name__, line))

			# User Objects
			#TODO: There is probably a race condition here,
			# no gaurantee that this window will exist when User objects come in,
			# needs a queue or something.
			if isinstance(response, User) and self.clientObject.mainWindowHandler:
				self.clientObject.mainWindowHandler.userList.updateUser(response)

			# Login Stuff
			elif isinstance(response, LoginResponse) and self.clientObject.loginHandler:
				if isinstance(response, LoginSuccess):
					self.clientObject.mainWindowHandler = \
						self.clientObject.windowFactory.buildWindow("mainWindow", MainWindowHandler)
					self.clientObject.mainWindowHandler.window.show_all()

					self.clientObject.loginHandler.window.destroy()
					self.clientObject.loginHandler = None
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
