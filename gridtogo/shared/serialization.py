import uuid
from zope.interface import Interface, implements
from networkobjects import *
import json

class ILineSerializer(Interface):
	"""Classes implementing this must serialize data to string containing no newlines."""
	def serialize(self, obj):
		"""
		Return the serialized string of an object.
		Raises an InvalidSerializedDataException if the passed data is invalid.
		"""

	def deserialize(self, str):
		"""Return the object of a serialized string."""

class InvalidSerializedDataException(Exception):
	def __init__(self, serializer):
		self.serializerName = serializer.__class__.__name__

	def __str__(self):
		return "This string was not generated by this version of "\
		       + self.serializerName + ", or this serializer has a bug."

class JSONSerializer(object):
	implements(ILineSerializer)

	def __init__(self, serializeableObjectsModule):
		self._jsonEncoder = self._CustomEncoder()
		self.serializeableObjectsModule = serializeableObjectsModule

	def serialize(self, obj):
		return self._jsonEncoder.encode(obj)

	#TODO: Use more reflection and make (de)serialization automatic!
	def deserialize(self, string):
		try:
			data = json.loads(string)
			if not data:
				raise ValueError("Data is null.")
		except ValueError:
			raise InvalidSerializedDataException(self)

		if not data.has_key('className'):
			raise InvalidSerializedDataException(self)

		class_ = getattr(self.serializeableObjectsModule, data['className'])
		if class_ is LoginRequest:
			return class_(
				data['firstName'],
				data['lastName'],
				data['password'],
				data['grid'])

		elif class_ is CreateUserRequest:
			return class_(
				data['firstName'],
				data['lastName'],
				data['password'],
				data['email'])

		elif class_ is CreateRegionRequest:
			return class_(
				uuid.UUID(data['uuid']),
				data['gridName'],
				data['regionName'],
				data['location'])

		elif class_ is ResetPasswordRequest:
			return class_(data['firstName'], data['lastName'])

		#elif class_ is uuid.UUID:
		#	return class_(data['value'])

		elif class_ is LoginSuccess:
			r = class_(uuid.UUID(data['UUID']), data['grid'], data['email'])
			r.externalhost = data['externalhost']
			return r

		elif class_ is NATCheckRequest:
			return class_(data['ports'], data['processports'])

		elif class_ is NATCheckResponse:
			return class_(data['status'])

		elif issubclass(class_, DeltaObject):
			obj = None
			if class_ is DeltaUser:
				obj = DeltaUser(uuid.UUID(data['UUID']))
			elif class_ is DeltaRegion:
				obj = DeltaRegion(data['regionName'])
			else:
				obj = class_()

			for key in data:
				if key != 'className' and key != 'UUID':
					setattr(obj, key, data[key])
			return obj
		elif issubclass(class_, Deltable):
			obj = None
			if class_ is User:
				obj = User(
						uuid.UUID(data['UUID']), data['firstName'],
						data['lastName'],data['online'], data['NATStatus'],
						data['moderator'], data['gridHost'],
						data['gridHostActive'])
			elif class_ is Region:
				uhosts = []
				for host in data['hosts']:
					uhosts = [uuid.UUID(host)] + uhosts
				obj = Region(
						data['regionName'], data['location'],
						data['currentHost'], uhosts)
			return obj

		else:
			try:
				return class_()
			# We have no idea if the constructor needs more info or not.
			except TypeError:
				raise InvalidSerializedDataException(self)

	class _CustomEncoder(json.JSONEncoder):
		def default(self, obj):
			# The decoder looks for the className to choose decoding scheme.
			data = {'className': obj.__class__.__name__}

			if isinstance(obj, LoginRequest):
				data['firstName'] = obj.firstName
				data['lastName'] = obj.lastName
				data['password'] = obj.password
				data['grid'] = obj.grid

			elif isinstance(obj, CreateUserRequest):
				data['firstName'] = obj.firstName
				data['lastName'] = obj.lastName
				data['password'] = obj.password
				data['email'] = obj.email

			elif isinstance(obj, ResetPasswordRequest):
				data['firstName'] = obj.firstName
				data['lastName'] = obj.lastName

			elif isinstance(obj, uuid.UUID):
				return str(obj)

			elif isinstance(obj, Deltable):
				for a in obj.attributes:
					data[a] = getattr(obj, a)

			elif isinstance(obj, DeltaObject):
				for a in obj.attributes:
					if hasattr(obj, a):
						data[a] = getattr(obj, a)

			elif isinstance(obj, LoginSuccess):
				data['UUID'] = obj.UUID
				data['grid'] = obj.grid
				data['email'] = obj.email
				data['externalhost'] = obj.externalhost

			elif isinstance(obj, CreateRegionRequest):
				data['uuid'] = obj.uuid
				data['gridName'] = obj.gridName
				data['regionName'] = obj.regionName
				data['location'] = obj.location

			elif isinstance(obj, NATCheckRequest):
				data['ports'] = obj.ports
				data['processports'] = obj.processports

			elif isinstance(obj, NATCheckResponse):
				data['status'] = obj.status

			return data
