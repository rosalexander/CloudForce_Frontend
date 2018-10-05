import requests
import time
import sqlite3

DATABASE = 'database.db'


def poll_humidity():	
	response = requests.get('https://us.wio.seeed.io/v1/node/GroveTempHumD1/humidity?access_token=8404488f6918fedac5c894255cf58d88')
	data = response.json()
	return data

def poll_lux():	
	response = requests.get('https://us.wio.seeed.io/v1/node/GroveDigitalLightI2C0/lux?access_token=8404488f6918fedac5c894255cf58d88')
	data = response.json()
	return data



running = True

conn = sqlite3.connect(DATABASE)
cur = conn.cursor()

while running:
	try:
		humidity = poll_humidity()['humidity']
		lux = poll_lux()['lux']
		print(humidity, lux)
		cur.execute("INSERT INTO readings(humidity, lux) VALUES (?, ?)", (humidity, lux))
		conn.commit()
		time.sleep(10)
	except KeyboardInterrupt:
		cur.close()
		conn.close()

