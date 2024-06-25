from socket import socket, AF_INET, SOCK_STREAM

class Client:

	def __init__(self, hostname, port):

		self.conn = socket(AF_INET, SOCK_STREAM)
		self.conn.connect((hostname, port))
		self.buffer = ''

	def login(self, password):
		assert self.wait_for('Please enter password:')
		self.send(password)
		assert self.wait_for('Logon successful.')
		for line in self.readlines():
			if 'Game name:' in line:
				self.name = line.split(':')[1].strip()
				break

	def wait_for(self, target):
		for line in self.readlines():
			if target in line:
				return True
		return False

	def readlines(self):
		flushed = not self.buffer
		while True:
			if flushed:
				data = self.conn.recv(1024)
				if not data:
					break # Connection closed
				self.buffer += data.decode('ascii')
			while '\n' in self.buffer:
				line, self.buffer = self.buffer.split('\n', 1)
				yield line.replace('\r', '')
			flushed = True
		if self.buffer:
			yield self.buffer

	def send(self, message):
		self.conn.sendall((message + '\n').encode('ascii'))
		self.conn.sendall('\n'.encode('ascii'))

	def close(self):
		self.conn.close()
