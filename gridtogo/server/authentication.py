import hashlib
from gridtogo.shared.networkobjects import *

class Authenticator(object):
	"""Checks LoginRequests against a Database."""
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
