from twisted.internet import gtk3reactor
gtk3reactor.install()

from gi.repository import Gtk
from twisted.internet import protocol, reactor
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

	def run(self):
		windowFactory = WindowFactory(self)
		loginWindow = windowFactory.buildWindow('loginWindow', LoginWindowHandler)
		loginWindow.show_all()

		#reactor.connectTCP("localhost", 8017, self.factory)
		reactor.run()

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
		self.currentProtocol = None

	def buildProtocol(self, addr):
		if not self.currentProtocol:
			self.currentProtocol = GTGClientProtocol(self.serializer)
			return self.currentProtocol
		else:
			raise Exception("BUG: Attempted to build a second protocol, client should not do this.")
