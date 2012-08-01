import hashlib
import database
import uuid
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
		hashedPassword = hashlib.sha256(loginRequest.password).hexdigest()
		userAccount = self.database.getUserAccountByName(loginRequest.firstName, loginRequest.lastName)
		if not userAccount:
			return UnknownUser(), None

		if userAccount.hashedPassword == hashedPassword:
			return LoginSuccess(userAccount.UUID, loginRequest.grid), userAccount
		else:
			return IncorrectPassword(), None

	def createUser(self, createUserRequest):
		if createUserRequest.firstName == ""\
			or createUserRequest.lastName == ""\
			or createUserRequest.email == ""\
			or createUserRequest.password == "":
			return InvalidData()

		userAccount = self.database.getUserAccountByName(createUserRequest.firstName, createUserRequest.lastName)
		#TODO: Possibly do additional checking such as password complexity, email validity, flood checking
		if userAccount:
			# Name conflict.
			return UsernameConflict()
		else:
			hashedPassword = hashlib.sha256(createUserRequest.password).hexdigest()
			userAccount = database.UserAccount(
				uuid.uuid4(),
				createUserRequest.firstName,
				createUserRequest.lastName,
				hashedPassword,
				createUserRequest.email)
			self.database.storeUserAccount(userAccount)
			return CreateUserSuccess()

	def resetPassword(self, resetPasswordRequest):
		#TODO: Actually process this request.
		# The password should not be immediately reset, or users could DOS each other like crazy.
		# Nor are we even able to send the user their current password.
		# New functionality will be required.
		return ResetPasswordResponse()
