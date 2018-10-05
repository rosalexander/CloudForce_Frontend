import requests
import datetime
import sqlite3



DATABASE = 'database.db'



def add_readings_to_route(route_id):

	conn = sqlite3.connect(DATABASE)

	cur = conn.cursor()

	iotJson = requests.get('http://132.145.129.245:5000/iot').json()


	for row in iotJson:

		date_string = row['Date'] + " " + row['Time']
		date_unformatted = datetime.datetime.strptime(date_string, "%Y/%m/%d %H:%M:%S")
		date_formatted = datetime.date.strftime(date_unformatted, "%Y-%m-%d %H:%M:%S")

		cur.execute("SELECT EXISTS(SELECT 1 FROM readings WHERE create_date = ?)", (date_formatted, ))

		id_exists = cur.fetchone()

		if id_exists[0] != 1:

			
			humidity = row['Humidity']
			lux = row['Light']
			temperature = row['Temperature']
			
			try:
				humidity = int(humidity.split('.')[0])
				lux = int(lux.split('.')[0])
				temperature = int(temperature.split('.')[0])
			except ValueError:
				print("Type error")
				pass

			cur.execute("INSERT INTO readings(route_id, temperature, humidity, lux, create_date) VALUES(?, ?, ?, ?, ?);", (route_id, temperature, humidity, lux, date_formatted))

	conn.commit()
	cur.close()
	conn.close()

def add_nfc_to_product(product_id):
	conn = sqlite3.connect(DATABASE)

	cur = conn.cursor()
	nfcJson = requests.get('http://132.145.129.245:5000/nfc').json()



	for row in nfcJson:

		if int(row['ID']) == product_id:

			date_string = "20" + row['Date Hatched'] + " " + row['Time']
			date_unformatted = datetime.datetime.strptime(date_string, "%Y/%m/%d %H:%M:%S")
			date_formatted = datetime.date.strftime(date_unformatted, "%Y-%m-%d %H:%M:%S")

			cur.execute("SELECT EXISTS(SELECT 1 FROM nfc WHERE product_id = ? AND scan_date = ?)", (product_id, date_formatted, ))
			id_exists = cur.fetchone()

			if id_exists[0] != 1:

				lon = row['Longitude']
				lat = row['Latitude']

				try:
					lon = float(lon)
					lat = float(lat)
				except ValueError:
					print("Type error")
					pass

				cur.execute("INSERT INTO nfc(product_id, lon, lat, scan_date) VALUES(?, ?, ?, ?)", (product_id, lon, lat, date_formatted))
	
	conn.commit()
	cur.close()
	conn.close()






