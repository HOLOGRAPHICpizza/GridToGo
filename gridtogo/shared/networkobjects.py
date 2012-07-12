class LoginRequest(object):
	def __init__(self, firstName, lastName, password, grid):
		self.firstName = firstName
		self.lastName = lastName
		self.password = password
		self.grid = grid
