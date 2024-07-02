from json import load, dump, dumps
from time import sleep, time
from threading import Thread
from functools import wraps
from datetime import date, timedelta
from random import choice

class Manager:

	def __init__(self, client, minutesperday):
		self.client = client
		self.minutesperday = minutesperday
		self.events = []
		self.commands = {
			'help': self.command_help,
			'tplist': self.command_tplist,
			'tp': self.command_tp,
			'tpadd': self.command_tpadd,
			'tpremove': self.command_tpremove,
			'sethome': self.command_sethome,
			'home': self.command_home,
			'visit': self.command_visit,
			'bag': self.command_bag,
			'wallet': self.command_wallet,
			'pay': self.command_pay,
			'pack': self.command_pack,
			'gimme': self.command_gimme,
			'horde': self.command_horde,
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
				if event == 'tp':
					self.portals[args[0]] = {
						'loc': location,
						'username': username,
					}
					self.save_portals()
					self.send('pm', [username, 'Portal set.'])
					self.events.remove(item)
					continue
				if event == 'home':
					self.players[username]['home'] = location # A coordinate list.
					self.save_players()
					self.send('pm', [username, 'Home set.'])
					self.events.remove(item)
					continue
				if event == 'pay':
					sender, amount = args
					self.players[sender]['balance'] -= amount
					self.players[username]['balance'] += amount
					self.save_players()
					self.send('pm', [sender, f'Sent {amount} coins to {username}.'])
					self.send('pm', [username, f'Received {amount} coins from {sender}.'])
					self.events.remove(item)
					continue
			if username.lower().startswith(str(key)):
				if event == 'visit':
					visitor, = args
					self.send('teleportplayer', [visitor, username])
					self.send('pm', [visitor, 'Zoop!'])
					self.send('pm', [username, f'{visitor} is here visit you.'])
					self.events.remove(item)
					continue
			if key == pid:
				if event == 'bag':
					self.players[username]['bag'] = args # A coordinate list.
					self.save_players()
					self.events.remove(item)
					continue
			if time() > expires:
				if event == 'pay':
					self.send('pm', [args[0], 'Recipient not found. Players must be online to receive funds.'])
				if event == 'visit':
					self.send('pm', [args[0], 'Player not found.'])
				self.events.remove(item)

	def handle_bag(self, pid, location):
		if location == [0, 0, 0]:
			return # Bag not in world yet.
		self.trigger('bag', pid, location)
		self.send('listplayers', [])

	def handle_kill(self, username, entity):
		self.init_player(username)
		if entity.startswith('zombie'):
			print(f' x {username}: {entity}')
			self.players[username]['balance'] += 1

	def handle_time(self, days, hours, minutes):
		horde = (days // 7 + 1) * 7
		duration = timedelta(days=horde - days, hours=22 - hours, minutes=0 - minutes)
		seconds = duration.total_seconds() * (self.minutesperday / 1440)
		hands = [
			('hour', int(seconds // 3600)),
			('minute', int((seconds % 3600) // 60)),
		]
		time = ' and '.join(
			[f'{value} {label}' + ('' if value == 1 else 's') for label, value in hands if value]
		)
		for item in self.events[:]:
			event, username = item[:2]
			self.send('pm', [username, f'Blood moon is on day [ffff00]{horde}[ff0000].'])
			sleep(0.25)
			self.send('pm', [username, f'It begins in [ffff00]{time} [ff0000]IRL.'])
			self.events.remove(item)

	def handle_command(self, username, command, args):
		self.init_player(username)
		if not command in self.commands:
			self.send('pm', [username, 'Unknown command. Type /help to list commands.'])
			return
		print(f' > {username}: /{command} {args}')
		response = self.commands[command](username, args)
		if response:
			self.send('pm', [username, response])

	def command_help(self, username, args):
		Thread(target=self.help_sender, args=(username,)).start()
		return None

	def command_tplist(self, username, args):
		return ', '.join([f'{p}' for p in sorted(self.portals.keys())])

	def command_tp(self, username, args):
		portal = args.lower()
		if not portal in self.portals.keys():
			return 'No such portal. Check /tplist again?'
		if not self.pay_fee(username, 1):
			return 'Insufficient funds. Cost is 1 coin.'
		self.send('teleportplayer', [username] + self.portals[portal]['loc'])
		return f'Welcome to {portal}!'

	def command_tpadd(self, username, args):
		portal = args.lower()
		if portal in self.portals:
			return 'This portal already exists.'
		if not self.pay_fee(username, 50):
			return 'Insufficient funds. Cost is 50 coins.'
		self.trigger('tp', username, [portal.lower()])
		self.send('listplayers', [])
		return None

	def command_tpremove(self, username, args):
		portal = args.lower()
		if not portal in self.portals:
			return 'No such portal. Check /tplist again?'
		if not self.portals[portal]['username'] == username:
			return 'You do not own this portal.'
		assert self.pay_fee(username, -50)
		del self.portals[portal]
		self.save_portals()
		return 'Removed teleport location. Refunded 50 coins.'

	def command_sethome(self, username, args):
		if not self.pay_fee(username, 10):
			return 'Insufficient funds. Cost is 10 coins.'
		self.trigger('home', username, [])
		self.send('listplayers', [])
		return None

	def command_home(self, username, args):
		home = self.players[username].get('home', None)
		if not home:
			return 'Cannot find home. Please use /sethome first.'
		self.send('teleportplayer', [username] + home)
		return 'Welcome home!'

	def command_visit(self, username, args):
		if not self.pay_fee(username, 1):
			return 'Insufficient funds. Cost is 1 coin.'
		if not args:
			return 'Usage: /visit <username>'
		self.trigger('visit', args.lower(), [username])
		self.send('listplayers', [])
		return None
		# TODO security
		# TODO more responsive error when player not found

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
		self.trigger('pay', recipient, [username, amount])
		self.send('listplayers', [])
		return None

	def command_pack(self, username, args):
		self.init_player(username)
		if self.players[username].get('pack', False):
			return f'Sorry, you already got your starter pack.'
		self.give_items(username, [
			('foodShamChowder', 10),
			('drinkJarPureMineralWater', 10),
			('medicalFirstAidBandage', 5),
			('drugHerbalAntibiotics', 5),
		])
		self.players[username]['pack'] = True
		self.save_players()
		return f'Enjoy your starter pack!'

	def command_gimme(self, username, args):
		self.init_player(username)
		today = date.today().strftime('%Y-%m-%d')
		gimme = self.players[username].get('gimme', None)
		if gimme == today:
			return f'Sorry, you already got your free items today.'
		candy = [
			'drugCovertCats',
			'drugEyeKandy',
			'drugHackers',
			'drugHealthBar',
			'drugJailBreakers',
			'drugNerdTats',
			'drugOhShitzDrops',
			'drugRockBusters',
			'drugSkullCrushers',
			'drugSugarButts',
		]
		ammo = [
			'ammoBundle9mmBulletBall',
			'ammoBundle44MagnumBulletBall',
			'ammoBundle762mmBulletBall',
			'ammoBundleShotgunShell',
		]
		self.give_items(username, [
			(choice(candy), 1),
			(choice(ammo), 1),
			('questRewardT1SkillMagazineBundle', 1),
		])
		self.players[username]['gimme'] = today
		self.save_players()
		return f'Enjoy your free items!'

	def give_items(self, username, items):
		for item, amount in items:
			self.send('give', [username, item, amount])

	def command_horde(self, username, args):
		self.trigger('horde', username, [])
		self.send('gettime', [])
		return None

	def help_sender(self, username):
		# We can't spam the chat too quickly.
		# This takes a while, so it's in a thread.
		lines = [
			'/help - This help menu',
			'/tplist - List portals',
			'/tp <portal> - Go to portal (1)',
			'/tpadd <portal> - Add portal (50)',
			'/tpremove <portal> - Remove portal',
			'/sethome - Set home location (10)',
			'/home - Go to home location',
			'/visit <username> - Go to a player (1)',
			'/bag - Go to bag location (1)',
			'/wallet - Your coin balance',
			'/pay <amount> <username> - Send coins',
			'/pack - Get your one-time starter pack',
			'/gimme - Get your free daily items',
			'/horde - How long until blood moon?',
		]
		for line in lines:
			colors = [
				('/', '[ffaa00]/'), # Command in orange
				('- ', '[00ff00]'), # Comments in green
				('<', '[ffff00]<'), # Arguments in yellow
				('(', '[00aaaa]('), # Fee in blue
			]
			for code, color in colors:
				line = line.replace(code, color)
			self.send('pm', [username, line])
			sleep(0.25) # Plus 0.25 built in to send()
