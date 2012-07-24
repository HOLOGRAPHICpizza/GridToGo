from twisted.internet import gtk3reactor
gtk3reactor.install()

from gi.repository import Gtk
from twisted.internet import protocol, reactor, endpoints, defer
from twisted.protocols import basic
from gridtogo.shared import serialization, networkobjects
from gridtogo.shared.networkobjects import *
from ui.windows import *

PRINT_PACKETS = True

#TODO: Move this test code to a different module and make this the real client
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

		# list of functions to call when we get a connection
		# passes a reference to a Protocol to each
		self.callOnConnected = []
		#TODO: implement a callOnConnectionFailed list

	def run(self):
		self.windowFactory = WindowFactory(self)
		self.loginHandler = self.windowFactory.buildWindow('loginWindow', LoginWindowHandler)
		self.loginHandler.window.show_all()

		popup = Gtk.Window()

		reactor.run()

	def attemptConnection(self, spinnerParent, host, port, timeout):
		if self.protocol:
			# assume we are already connected and call onConnected again
			self.onConnected(self.protocol)
		if self.attempt:
			print("connection attempt already in progress!")
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
				print("IN : %s | %s" % (response.__class__.__name__, line))

			# Login Stuff
			if isinstance(response, LoginResponse) and self.clientObject.loginHandler:
				if isinstance(response, LoginSuccess):
					self.clientObject.loginHandler.window.destroy()
					self.clientObject.loginHandler = None

					self.clientObject.mainWindowHandler = \
						self.clientObject.windowFactory.buildWindow("mainWindow", MainWindowHandler)
					self.clientObject.mainWindowHandler.window.show_all()
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
			print("Server sent bad data.")
			self.transport.loseConnection()

	def writeRequest(self, request):
		line = self.serializer.serialize(request)
		if PRINT_PACKETS:
			print("OUT: %s | %s" % (request.__class__.__name__, line))
		self.transport.write(line + "\r\n")

class GTGClientFactory(protocol.ClientFactory):
	def __init__(self, clientObject):
		self.serializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))
		self.clientObject = clientObject

	def buildProtocol(self, addr):
		return GTGClientProtocol(self.clientObject, self.serializer)
