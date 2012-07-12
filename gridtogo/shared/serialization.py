from zope.interface import Interface, implements

class ISerializer(Interface):
	def serialize(self, obj):
		"""Return the serialized string of an object."""

	def deserialize(self, str):
		"""Return the object of a serialized string."""

class JSONSerializer(object):
	implements(ISerializer)

	def serialize(self, obj):
		return "Not implemented."

	def deserialize(self, str):
		return "Not implemented."

