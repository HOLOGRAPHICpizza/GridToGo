from twisted.protocols.basic import LineReceiver
from gridtogo.shared import *
import gridtogo.shared.networkobjects

class GridToGoServer(object):
	def __init__(self, port):
		self.port = port

	def run(self):
		loginRequest = LoginRequest("torco", "man", "scudz", "mygrid")

		serializer = ILineSerializer(JSONSerializer(networkobjects))

		string = serializer.serialize(loginRequest)

		instance = serializer.deserialize(string)
		print(instance.firstName)


class GTGProtocol(LineReceiver):
	"""
	Stateful communication with clients through a one-line-per-request serialization format.
	Any serialization can be used, default implementation is JSON.
	One of these is created for each client connection.
	"""
	pass
