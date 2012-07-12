from twisted.protocols.basic import LineReceiver

class GridToGoServer(object):
	def __init__(self, port):
		self.port = port

	def run(self):
		print("Hello, server world!")


class GTGProtocol(LineReceiver):
	"""Stateful communication with clients through a one-line-per-request serialization format.
	Any serialization can be used, default implementation is JSON.
	One of these is created for each client connection."""
	pass
