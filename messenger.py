from time import sleep
from threading import Thread, Event
from datetime import datetime

class Messenger:

	def __init__(self, client, restarttime):
		self.client = client
		self.restarttime = restarttime
		self.haulting = Event()
		self.thread = Thread(target=self.shutdown_notification)
		self.thread.start()
		self.client.send('say "The server manager is back online!"')

	def shutdown_notification(self):
		(hours, minutes) = map(int, self.restarttime.split(':'))
		while not self.haulting.is_set():
			now = datetime.utcnow()
			restart = datetime(now.year, now.month, now.day, hours, minutes, 0)
			remaining = int((restart - now).total_seconds() // 60)
			if remaining in [30, 20, 10, 5, 4, 3, 2, 1]:
				self.client.send(f'say "The server will restart in [ff0000]{remaining}[ffffff] minutes!"')
			if self.haulting.wait(60):
				self.client.send('say "The server manager has shut down."')
