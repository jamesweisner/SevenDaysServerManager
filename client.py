from socket import socket, AF_INET, SOCK_STREAM, error, timeout
from time import sleep

class Client:

	def __init__(self, hostname, port):
		tries = 0
		while True:
			try:
				self.conn = socket(AF_INET, SOCK_STREAM)
				self.conn.settimeout(5)
				self.conn.connect((hostname, port))
				self.conn.settimeout(None)
				break # Success!
			except (timeout, error) as e:
				tries += 1
				for seconds in range(5, 0, -1):
					print(f' [{tries}] Connection failed, retrying in {seconds}...', end='\r')
					sleep(1)
				print(f' [{tries}] Connection failed, retrying...     ', end='\r')
		if tries:
			print('') # Needed line break
		self.buffer = ''

	def login(self, password):
		assert self.wait_for('Please enter password')
		self.send(password)
		if not self.wait_for('Logon successful', 'Password incorrect'):
			return False
		for line in self.readlines():
			if 'Game name:' in line:
				self.name = line.split(':')[1].strip()
				break
		assert self.name
		return True

	def wait_for(self, target, failure=None):
		for line in self.readlines():
			if target in line:
				return True
			if failure and failure in line:
				return False
		return False

	def readlines(self):
		flushed = not self.buffer
		with open('logs.txt', 'a') as file:
			while True:
				if flushed:
					data = self.conn.recv(1024)
					if not data:
						break # Connection closed
					self.buffer += data.decode('ascii')
				while '\r\n' in self.buffer:
					line, self.buffer = self.buffer.split('\r\n', 1)
					file.write(line.encode('ascii').decode('utf-8') + u'\n')
					file.flush()
					yield line
				flushed = True

	def send(self, message):
		self.conn.sendall((message + '\n').encode('ascii'))
		self.conn.sendall('\n'.encode('ascii'))
