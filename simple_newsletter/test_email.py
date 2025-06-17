import os
import requests
def send_simple_message():
  	return requests.post(
  		"https://api.eu.mailgun.net/v3/mg.vfll.de/messages",
  		auth=("api", os.getenv('MAILGUN_API_KEY', 'MAILGUN_API_KEY')),
  		data={"from": "Mailgun Sandbox <postmaster@mg.vfll.de>",
			"to": "Ulrich Kilian <uk@science-and-more.de>",
  			"subject": "Hello Ulrich Kilian",
  			"text": "Congratulations Ulrich Kilian, you just sent an email with Mailgun! You are truly awesome!"})