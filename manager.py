from json import load, dump, dumps

class Manager:

	# TODO implement zcoins and charge for services

	def __init__(self, client):
		self.client = client
		self.events = []
		self.commands = {
			'help': self.command_help,
			'listtele': self.command_listtele,
			'settele': self.command_settele,
			'remtele': self.command_remtele,
			'tele': self.command_tele,
			'sethome': self.command_sethome,
			'home': self.command_home,
			'visit': self.command_visit,
			'bag': self.command_bag,
		}
		try:
			with open('players.json') as file:
				self.players = load(file)
		except FileNotFoundError:
			self.players = {}
			self.save_players()
		try:
			with open('portals.json') as file:
				self.portals = load(file)
		except FileNotFoundError:
			self.portals = {}
			self.save_portals()

	def save_players(self):
		with open('players.json', 'w') as file:
			dump(self.players, file)

	def save_portals(self):
		with open('portals.json', 'w') as file:
			dump(self.portals, file)

	def send(self, command, args):
		self.client.send(' '.join([command] + [dumps(p) for p in args]))

	def set_player(self, pid, username, location):
		if not username in self.players:
			self.players[username] = {}
		for event in self.events[:]:
			mode, key, arg = event
			if key == username:
				if mode == 'tele':
					self.portals[arg] = {
						'loc': location,
						'username': username,
					}
					self.save_portals()
					self.events.remove(event)
					self.send('pm', [username, 'Portal set.'])
				if mode == 'home':
					self.players[username]['home'] = location
					self.save_players()
					self.events.remove(event)
					self.send('pm', [username, 'Home set.'])
			if key == pid:
				if mode == 'bag':
					self.players[username]['bag'] = location
					self.save_players()
					self.events.remove(event)

	def set_bag(self, pid, location):
		self.send('listplayers', [])
		self.events.append(('bag', pid, location))

	def handle(self, username, command, args):
		if not command in self.commands:
			self.send('pm', [username, 'Unknown command. Type /help to list commands.'])
			return
		print(f' > {username}: /{command} {args}')
		self.commands[command](username, args)

	def command_help(self, username, args):
		self.send('pm', [username, ' '.join([f'/{c}' for c in self.commands.keys()])])

	def command_listtele(self, username, args):
		self.send('pm', [username, ', '.join([f'{p}' for p in self.portals.keys()])])

	def command_settele(self, username, args):
		if args in self.portals:
			self.send('pm', [username, 'This portal already exists.'])
			return
		self.send('pm', [username, 'Setting teleport location, hold still...'])
		self.send('listplayers', [])
		self.events.append(('tele', username, args))

	def command_remtele(self, username, args):
		if not args in self.portals:
			self.send('pm', [username, 'No such portal. Check /listtele again?'])
			return
		if not self.portals[args].get('username', '') == username:
			self.send('pm', [username, 'You do not own this portal.'])
			return
		del self.portals[args]
		self.save_portals()
		self.send('pm', [username, 'Removed teleport location.'])

	def command_tele(self, username, args):
		loc = self.portals[args].get('loc', None)
		if not loc:
			self.send('pm', [username, 'No such portal. Check /listtele again?'])
			return
		self.send('teleportplayer', [username] + loc)
		self.send('pm', [username, f'Welcome to {args}!'])

	def command_sethome(self, username, args):
		self.send('pm', [username, 'Setting home location, hold still...'])
		self.send('listplayers', [])
		self.events.append(('home', username, None))

	def command_home(self, username, args):
		home = self.players[username].get('home', None)
		if not home:
			self.send('pm', [username, 'Cannot find home. Please use /sethome first.'])
			return
		self.send('teleportplayer', [username, home])
		self.send('pm', [username, 'Welcome home!'])

	def command_visit(self, username, args):
		self.send('pm', [username, 'Zoop!'])
		self.send('teleportplayer', [username, args])

	def command_bag(self, player, args):
		bag = self.players[username].get('bag', None)
		if not bag:
			self.send('pm', [username, 'Cannot locate bag.'])
			return
		self.send('pm', [username, 'Zoop!'])
		self.send('teleportplayer', [username] + bag)
