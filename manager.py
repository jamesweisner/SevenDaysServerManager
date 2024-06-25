from json import load, dump, dumps
from functools import wraps
from time import time

class Manager:

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
			'wallet': self.command_wallet,
			'pay': self.command_pay,
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
			dump(self.players, file, indent=2)

	def save_portals(self):
		with open('portals.json', 'w') as file:
			dump(self.portals, file, indent=2)

	def send(self, command, args):
		self.client.send(' '.join([command] + [dumps(p) for p in args]))

	def pay_fee(self, username, amount):
		if self.players[username]['balance'] < amount:
			return False
		self.players[username]['balance'] -= amount
		self.save_players()
		return True

	def trigger(self, event, key, args):
		self.events.append((event, key, args, time() + 5))

	def init_player(self, username):
		if not username in self.players:
			self.players[username] = { 'balance': 0 }
			self.save_players()

	def handle_player(self, pid, username, location):

		# Track every player we see.
		self.init_player(username)

		# Work on a copy of the list so we can saefly remove items from the original.
		for item in self.events[:]:
			event, key, args, expires = item
			if key == username:
				if event == 'tele':
					self.portals[args[0]] = {
						'loc': location,
						'username': username,
					}
					self.save_portals()
					self.events.remove(item)
					self.send('pm', [username, 'Portal set.'])
					continue
				if event == 'home':
					self.players[username]['home'] = location # A coordinate list.
					self.save_players()
					self.events.remove(item)
					self.send('pm', [username, 'Home set.'])
					continue
				if event == 'pay':
					sender, amount = args
					self.players[sender]['balance'] -= amount
					self.players[username]['balance'] += amount
					self.save_players()
					self.events.remove(item)
					self.send('pm', [sender, f'Sent {amount} coins to {username}.'])
					self.send('pm', [username, f'Received {amount} coins from {sender}.'])
					continue
			if key == pid:
				if event == 'bag':
					self.players[username]['bag'] = args # A coordinate list.
					self.save_players()
					self.events.remove(item)
					continue
			if time() > expires:
				if event == 'pay':
					self.send('pm', [sender, f'Recipient not found. Players must be online to receive funds.'])
				self.events.remove(item)

	def handle_bag(self, pid, location):
		self.init_player(username)
		self.send('listplayers', [])
		self.trigger('bag', pid, location)
		# TODO not working?

	def handle_kill(self, username, entity):
		self.init_player(username)
		print(f' x {username}: {entity}')
		if entity.startswith('zombie'):
			self.players[username]['balance'] += 1

	def handle_command(self, username, command, args):
		self.init_player(username)
		if not command in self.commands:
			self.send('pm', [username, 'Unknown command. Type /help to list commands.'])
			return
		print(f' > {username}: /{command} {args}')
		response = self.commands[command](username, args)
		self.send('pm', [username, response])

	def command_help(self, username, args):
		return ' '.join([f'/{c}' for c in self.commands.keys()])
		# TODO show arguments & coin costs

	def command_listtele(self, username, args):
		return ', '.join([f'{p}' for p in self.portals.keys()])

	def command_settele(self, username, args):
		if args in self.portals:
			return 'This portal already exists.'
		if not self.pay_fee(username, 50):
			return 'Insufficient funds. Cost is 50 coins.'
		self.send('listplayers', [])
		self.trigger('tele', username, [args])
		return 'Setting teleport location, hold still...'

	def command_remtele(self, username, args):
		if not args in self.portals:
			return 'No such portal. Check /listtele again?'
		if not self.portals[args]['username'] == username:
			return 'You do not own this portal.'
		assert self.pay_fee(username, -50)
		del self.portals[args]
		self.save_portals()
		return 'Removed teleport location. Refunded 50 coins.'

	def command_tele(self, username, args):
		if not args in self.portals:
			return 'No such portal. Check /listtele again?'
		if not self.pay_fee(username, 1):
			return 'Insufficient funds. Cost is 1 coin.'
		self.send('teleportplayer', [username] + self.portals[args]['loc'])
		return f'Welcome to {args}!'

	def command_sethome(self, username, args):
		if not self.pay_fee(username, 10):
			return 'Insufficient funds. Cost is 10 coins.'
		self.send('listplayers', [])
		self.trigger('home', username, [])
		return 'Setting home location, hold still...'

	def command_home(self, username, args):
		home = self.players[username].get('home', None)
		if not home:
			return 'Cannot find home. Please use /sethome first.'
		self.send('teleportplayer', [username] + home)
		return 'Welcome home!'

	def command_visit(self, username, args):
		if not self.pay_fee(username, 1):
			return 'Insufficient funds. Cost is 1 coin.'
		# TODO what if the player is not found?
		self.send('teleportplayer', [username, args])
		return 'Zoop!'

	def command_bag(self, username, args):
		bag = self.players[username].get('bag', None)
		if not bag:
			return 'Cannot locate bag.'
		if not self.pay_fee(username, 1):
			return 'Insufficient funds. Cost is 1 coin.'
		self.send('teleportplayer', [username] + bag)
		return 'Zoop!'

	def command_wallet(self, username, args):
		balance = self.players[username]['balance']
		return f'You have {balance} coins in your wallet.'

	def command_pay(self, username, args):
		try:
			amount, recipient = args.split(' ', 1)
			amount = int(amount)
			assert amount > 0
			assert recipient
		except:
			return f'Usage: /pay <amount> <username>'
		balance = self.players[username]['balance']
		if amount > balance:
			return f'You only have {balance} coins in your wallet.'
		return f'Sending payment...'
		self.trigger('pay', recipient, [username, amount])
		self.send('listplayers', [])
