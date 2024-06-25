import config
from re import compile
from client import Client
from manager import Manager

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

print(f'Connecting to {config.hostname}:{config.port}')
client = Client(config.hostname, config.port)

print(f'Logging in...')
client.login(config.password)

manager = Manager(client)

try:
	print(f'Managing server: {client.name}')
	for line in client.readlines():

		# Watch for player list updates.
		match = player_regex.match(line)
		if match:
			pid, username, location = match.groups()
			location = [round(float(d)) for d in location.split(', ')]
			manager.set_player(int(pid), username, location)
			continue

		# Watch for dropped bags.
		match = bag_regex.match(line)
		if match:
			pid, location = match.groups()
			location = [round(float(d)) for d in location.split(', ')]
			manager.set_bag(int(pid), location)
			continue

		# Watch player chat for commands.
		match = chat_regex.match(line)
		if match:
			username, message = match.groups()
			if not message[0] == '/':
				continue # Not a command.
			command, args = (message[1:] + ' ').split(' ', 1)
			manager.handle(username, command, args.strip())
			continue

except KeyboardInterrupt:
	print('Shutting down...')
	client.close()
