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
	def __init__(self, projectRoot):
		self.projectRoot = projectRoot

	def run(self):
		windowFactory = WindowFactory(self)
		loginWindow = windowFactory.buildWindow('loginWindow', LoginWindowHandler)
		loginWindow.show_all()

		#reactor.connectTCP("localhost", 8017, GTGClientFactory())
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

	def _writeRequest(self, request):
		line = self.serializer.serialize(request)
		#print("OUT: " + line)
		self.transport.write(line + "\r\n")

class GTGClientFactory(protocol.ClientFactory):
	def __init__(self):
		self.serializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))

	def buildProtocol(self, addr):
		return GTGClientProtocol(self.serializer)
