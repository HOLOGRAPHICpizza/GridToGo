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

		self.loginHandler = None
		self.createUserWindowHandler = None

		# list of functions to call when we get a connection
		# passes a reference to a Protocol to each
		self.callOnConnected = []
		#TODO: implement a callOnConnectionFailed list

	def run(self):
		windowFactory = WindowFactory(self)
		self.loginHandler = windowFactory.buildWindow('loginWindow', LoginWindowHandler)
		self.loginHandler.window.show_all()

		popup = Gtk.Window()

		reactor.run()

	def attemptConnection(self, host, port, timeout):
		if self.protocol:
			# assume we are already connected and call onConnected again
			self.onConnected(self.protocol)
		if self.attempt:
			print("connection attempt already in progress!")
			return

		self.endpoint = endpoints.TCP4ClientEndpoint(reactor, host, port, timeout)
		self.attempt = self.endpoint.connect(self.factory)
		self.attempt.addCallback(self.onConnected)
		self.attempt.addErrback(self.onConnectionFailed)

	def onConnected(self, protocol):
		self.attempt = None
		self.protocol = protocol
		for f in self.callOnConnected:
			if callable(f):
				f(protocol)

	def onConnectionFailed(self, failure):
		self.attempt = None
		self.endpoint = None
		print(failure.value)

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

			if isinstance(response, CreateUserResponse):
				if isinstance(response, CreateUserSuccess):
					self.clientObject.createUserWindowHandler.onCreateUserSuccess()
				else:
					dialog = Gtk.MessageDialog(self.clientObject.createUserWindowHandler.window,
						Gtk.DialogFlags.MODAL,
						Gtk.MessageType.ERROR,
						Gtk.ButtonsType.OK,
						response.message)
					dialog.run()
					dialog.destroy()

			# if the message is about a successful login, then open the main form.
			# If not, simply generate a response as to why.
			if self.clientObject.loginHandler:
				if isinstance(response, LoginSuccess):
					pass
					#self.clientObject.loginHandler.
				elif isinstance(response, IncorrectPassword):
					print response.message
				elif isinstance(response, UnknownUser):
					print response.message

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
		#if not self.currentProtocol:
		#	self.currentProtocol = GTGClientProtocol(self.serializer)
		#	return self.currentProtocol
		#else:
		#	raise Exception("BUG: Attempted to build a second protocol, client should not do this.")
