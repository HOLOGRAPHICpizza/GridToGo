# "Delta Objects"

class DeltaObject(object):
	def __init_(self):
		self.attributes = ()
	
	def applyDelta(self, deltaObject):
		"""Copy all the valid and existing attributes from detaObject into this object."""
		for a in deltaObject.attributes:
			if hasattr(deltaObject, a):
				setattr(self, a, getattr(deltaObject, a))
		return self

class User(DeltaObject):
	"""
	These are only relevant in the context of a grid.
	UserAccount is the record of the user independent of a grid.
	"""
	def __init__(self, UUID):
		self.attributes = ('UUID', 'firstName', 'lastName', 'online', 'NATStatus', 'moderator', 'gridHost', 'gridHostActive')
		self.UUID = UUID

# Account management stuff

class CreateUserRequest(object):
	def __init__(self, firstName, lastName, password, email):
		self.firstName = firstName
		self.lastName = lastName
		self.password = password
		self.email = email

class CreateUserResponse(object):
	"""Subclasses of this are returned by authentication services."""
	def __init__(self):
		self.message = 'Unknown error creating account, this is probably a bug.'

class InvalidData(CreateUserResponse):
	def __init__(self):
		self.message = 'The name, password, or email you specified is not valid.'

class UsernameConflict(CreateUserResponse):
	def __init__(self):
		self.message = 'Someone with the same name already exists in the database.'

class CreateUserSuccess(CreateUserResponse):
	def __init__(self):
		self.message = 'Account successfully created.'

class ResetPasswordRequest(object):
	def __init__(self, firstName, lastName):
		self.firstName = firstName
		self.lastName = lastName

class ResetPasswordResponse(object):
	def __init__(self):
		self.message = "Instructions for accessing this account have been sent to the email address this account was registered with."

# Login stuff

class LoginRequest(object):
	def __init__(self, firstName, lastName, password, grid):
		self.firstName = firstName
		self.lastName = lastName
		self.password = password
		self.grid = grid

class LoginResponse(object):
	"""Subclasses of this are returned by authentication services."""
	def __init__(self):
		self.message = 'Unknown authentication error, this is probably a bug.'

class UnknownUser(LoginResponse):
	def __init__(self):
		self.message = 'User not found.'

class IncorrectPassword(LoginResponse):
	def __init__(self):
		self.message = 'Incorrect password.'

class NotGridMember(LoginResponse):
	"""The user is not on the members list of a members-only grid."""
	def __init__(self):
		self.message = 'You are not authorized to join this grid.'

class TooManyAttempts(LoginResponse):
	"""The user has attempted to log in too many times in too short of a period."""
	def __init__(self):
		self.message = 'Too many login attempts. Please wait and try again.'

class LoginSuccess(LoginResponse):
	def __init__(self):
		self.message = 'Login successful.'
