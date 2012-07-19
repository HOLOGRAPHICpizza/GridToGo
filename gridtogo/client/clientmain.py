from twisted.internet import gtk3reactor
gtk3reactor.install()

from gi.repository import Gtk
from twisted.internet import protocol, reactor, endpoints, defer
from twisted.protocols import basic
from gridtogo.shared import serialization, networkobjects
from gridtogo.shared.networkobjects import *
from ui.windows import *

#TODO: Move this test code to a different module and make this the real client
class GridToGoClient(object):
	"""
	One instance of this class should exist in our application.
	This holds shared state for the whole program.
	"""
	def __init__(self, projectRoot):
		self.projectRoot = projectRoot
		self.factory = GTGClientFactory()

		self.endpoint = None
		self.attempt = None
		self.protocol = None

		# list of functions to call when we get a connection
		# passes a reference to a Protocol to each
		self.callOnConnected = []
		#TODO: implement a callOnConnectionFailed list

	def run(self):
		windowFactory = WindowFactory(self)
		self.loginHandler = windowFactory.buildWindow('loginWindow', LoginWindowHandler)
		self.loginHandler.window.show_all()

		#reactor.connectTCP("localhost", 8017, self.factory)
		reactor.run()

	def attemptConnection(self, host, port, timeout):
		if self.attempt:
			print("attempt already in progress!")
			return
		if self.endpoint:
			print("already connected!")
			return

		self.endpoint = endpoints.TCP4ClientEndpoint(reactor, host, port, timeout)
		self.attempt = self.endpoint.connect(self.factory)
		self.attempt.addCallback(self.onConnected)
		self.attempt.addErrback(self.onConnectionFailed)
		print("attempting connection...")

	def onConnected(self, protocol):
		print("connected")
		self.protocol = protocol
		for f in self.callOnConnected:
			f(protocol)

	def onConnectionFailed(self, failure):
		self.attempt = None
		self.endpoint = None
		print(failure.value)

	def stop(self):
		reactor.stop()

class GTGClientProtocol(basic.LineReceiver):
	def __init__(self, serializer):
		# Alias for convenience
		self.serializer = serializer

	def connectionMade(self):
		pass

	def lineReceived(self, line):

		#print("IN : " + line)

		try:
			#TODO: Perhaps in the future we should make (de)serialization operations asynchronous,
			# not sure if this is worth the effort/overhead or not.
			response = self.serializer.deserialize(line)

			#if the message is about a successful login, then open the main form.
			#If not, simply generate a response as to why.
			if isinstance(response, LoginSuccess):
				print response
			elif isinstance(response, IncorrectPassword):
				print response
			elif isinstance(response, UnknownUser):
				print response

				

			print(line + " | " + repr(response))

		except serialization.InvalidSerializedDataException:
			print("Server sent bad data.")
			self.transport.loseConnection()

	def writeRequest(self, request):
		line = self.serializer.serialize(request)
		#print("OUT: " + line)
		self.transport.write(line + "\r\n")

class GTGClientFactory(protocol.ClientFactory):
	def __init__(self):
		self.serializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))
		#self.currentProtocol = None

	def buildProtocol(self, addr):
		return GTGClientProtocol(self.serializer)
		#if not self.currentProtocol:
		#	self.currentProtocol = GTGClientProtocol(self.serializer)
		#	return self.currentProtocol
		#else:
		#	raise Exception("BUG: Attempted to build a second protocol, client should not do this.")
