from twisted.protocols.basic import LineReceiver
from ..shared import *

class GridToGoServer(object):
	def __init__(self, port):
		self.port = port

	def run(self):
		serializer = ILineSerializer(JSONSerializer())
		loginRequest = LoginRequest("torco", "man", "scudz", "mygrid")
		print(serializer.serialize(loginRequest))


class GTGProtocol(LineReceiver):
	"""
	Stateful communication with clients through a one-line-per-request serialization format.
	Any serialization can be used, default implementation is JSON.
	One of these is created for each client connection.
	"""
	pass
