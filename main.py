import config
from re import compile
from time import sleep
from client import Client
from manager import Manager
from traceback import print_exc

chat_regex = compile(
	# 2024-06-24T21:23:45 716.910 INF Chat (from '...', entity id '172', to 'Global'): 'PhysicsPolice': /test
	r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} \d+\.\d+ INF "
	r"Chat .+?: "
	r"'(?P<username>.+?)': (?P<message>.+)"
)

player_regex = compile(
	# 1. id=171, PhysicsPolice, pos=(1103.7, 35.1, -830.2), ...
	r"\d+\. id=(?P<pid>\d+), (?P<username>.+?), pos=\((?P<location>.+?)\).*"
)

bag_regex = compile(
	# 2024-06-24T21:23:45 716.910 INF 86805 EntityBackpack id 1097, plyrId 171, (1092.2, 35.2, -830.5) ...
	r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} \d+\.\d+ INF "
	r"\d+ EntityBackpack id \d+ plyrId (?P<pid>\d+), "
	r"\((?P<location>.+?)\).*"
)

kill_regex = compile(
	# 2024-06-25T15:08:39 64611.265 INF Entity zombieBurnt 2238 killed by PhysicsPolice 171
	r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} \d+\.\d+ INF "
	r"Entity (?P<entity>.+?) \d+ killed by (?P<username>.+?) \d+"
)

try:
	while True:

		print(f'Connecting to {config.hostname}:{config.port}')
		client = Client(config.hostname, config.port)

		print(f'Logging in...', end='\r')
		if not client.login(config.password):
			exit('Login failed!')

		manager = Manager(client)
		print(f'Managing server: {client.name}')

		try:
			for line in client.readlines():

				# Watch for player list updates.
				match = player_regex.match(line)
				if match:
					pid, username, location = match.groups()
					location = [round(float(d)) for d in location.split(', ')]
					manager.handle_player(int(pid), username, location)
					continue

				# Watch for dropped bags.
				match = bag_regex.match(line)
				if match:
					pid, location = match.groups()
					location = [round(float(d)) for d in location.split(', ')]
					manager.handle_bag(int(pid), location)
					continue

				# Watch player chat for commands.
				match = chat_regex.match(line)
				if match:
					username, message = match.groups()
					if not message[0] == '/':
						continue # Not a command.
					command, args = (message[1:] + ' ').split(' ', 1)
					manager.handle_command(username, command, args.strip())
					continue

				# Watch for Zombie kills.
				match = kill_regex.match(line)
				if match:
					entity, username = match.groups()
					manager.handle_kill(username, entity)
					continue

		except Exception:
			print_exc()

		print('Connection lost, reconnecting in 5 seconds...')
		sleep(5)

except KeyboardInterrupt:
	print('\nShutting down...')
