from zope.interface import Interface, implements

class LoginResponse(object):
	"""Subclasses of this are returned by authentication services."""
	self.message = 'Unknown authentication '

class UnknownUser(LoginResponse):
	pass

class IncorrectPassword(LoginResponse):
	pass

class NotGridMember(LoginResponse):
	"""The user is not on the members list of a members-only grid."""
	pass

class TooManyAttempts(LoginResponse):
	"""The user has attempted to log in too many times in too short of a period."""
	pass

class IAuthenticationService(Interface):

	def
