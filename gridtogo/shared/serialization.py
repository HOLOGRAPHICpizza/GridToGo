from zope.interface import Interface, implements
from networkobjects import *
import json

class ILineSerializer(Interface):
	"""Classes implementing this must serialize data to string containing no newlines."""
	def serialize(self, obj):
		"""Return the serialized string of an object."""

	def deserialize(self, str):
		"""Return the object of a serialized string."""


class JSONSerializer(object):
	implements(ILineSerializer)

	def __init__(self):
		self._jsonEncoder = self._CustomEncoder()

	def serialize(self, obj):
		return self._jsonEncoder.encode(obj)

	def deserialize(self, str):
		return "Not implemented."

	class _CustomEncoder(json.JSONEncoder):
		def default(self, obj):
			# The decoder looks for the className to choose decoding scheme.
			representation = {'className': obj.__class__.__name__}

			if isinstance(obj, LoginRequest):
				representation['firstName'] = obj.firstName
				representation['lastName'] = obj.lastName
				representation['password'] = obj.password
				representation['grid'] = obj.grid
				return representation


