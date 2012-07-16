import hashlib
from gridtogo.shared.networkobjects import *

class Authenticator(object):
	"""
	Checks LoginRequests against a Database.
	All methods may thow a DatabaseException.
	"""
	def __init__(self, database):
		self.database = database

	def authenticateUser(self, loginRequest):
		#TODO: Flood checking and grid member checking.
		hashedPassword = hashlib.sha224(loginRequest.password).hexdigest()
		userAccount = self.database.getUserAccountByName(loginRequest.firstName, loginRequest.lastName)
		if not userAccount:
			return UnknownUser()

		if userAccount.hashedPassword == hashedPassword:
			return LoginSuccess()
		else:
			return IncorrectPassword()

	def createUser(self, createUserRequest):
		userAccount = self.database.getUserAccountByName(createUserRequest.firstName, createUserRequest.lastName)
		#TODO: Possibly do additional checking such as password complexity, email validity
		if userAccount:
			# Name conflict.
			return UsernameConflict()
		else:
			# no name conflict
			return CreateUserSuccess()
