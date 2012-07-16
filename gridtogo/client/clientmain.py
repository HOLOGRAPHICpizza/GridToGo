from twisted.internet import protocol, reactor
from twisted.protocols import basic
from gridtogo.shared import serialization, networkobjects
from gridtogo.shared.networkobjects import *

#TODO: Move this test code to a different module and make this the real client
class GridToGoClient:
	def run(self):
		reactor.connectTCP("localhost", 8017, GTGClientFactory())
		reactor.run()

class GTGClientProtocol(basic.LineReceiver):
	def __init__(self, serializer):
		# Alias for convenience
		self.serializer = serializer

	def connectionMade(self):
		# try to create the same user twice
		createUserRequest = CreateUserRequest('generated', 'user', 'testpass', 'gridtgo@mailinator.com')
		self._writeRequest(createUserRequest)
		self._writeRequest(createUserRequest)

		# log in to the user incorrectly, then correctly
		loginRequest = LoginRequest('wrong', 'user', 'testpass', 'testgrid')
		self._writeRequest(loginRequest)
		loginRequest = LoginRequest('generated', 'user', 'wrongpass', 'testgrid')
		self._writeRequest(loginRequest)
		loginRequest = LoginRequest('generated', 'user', 'testpass', 'testgrid')
		self._writeRequest(loginRequest)

	def lineReceived(self, line):
		try:
			#TODO: Perhaps in the future we should make (de)serialization operations asynchronous,
			# not sure if this is worth the effort/overhead or not.
			response = self.serializer.deserialize(line)

			print(line + " | " + repr(response))

		except serialization.InvalidSerializedDataException:
			print("Server sent bad data.")
			self.transport.loseConnection()

	def _writeRequest(self, request):
		self.transport.write(self.serializer.serialize(request)+"\r\n")

class GTGClientFactory(protocol.ClientFactory):
	def __init__(self):
		self.serializer = serialization.ILineSerializer(serialization.JSONSerializer(networkobjects))

	def buildProtocol(self, addr):
		return GTGClientProtocol(self.serializer)
