import requests
import time
import sqlite3

DATABASE = 'database.db'


running = True

conn = sqlite3.connect(DATABASE)
cur = conn.cursor()


def setupDB():

	cur = conn.cursor()

	cur.execute("CREATE TABLE IF NOT EXISTS product( \
		product_id INTEGER PRIMARY KEY, \
		product_type text, \
		start_route INTEGER, \
		start_date TIMESTAMP, \
		end_date TIMESTAMP);")

	cur.execute("CREATE TABLE IF NOT EXISTS route( \
		route_id INTEGER PRIMARY KEY, \
		src_id INTEGER, \
		dest_id INTEGER, \
		next_route INTEGER, \
		start_date TIMESTAMP, \
		end_date TIMESTAMP);")

	cur.execute("CREATE TABLE IF NOT EXISTS location( \
		location_id INTEGER PRIMARY KEY, \
		location_name text);")

	cur.execute("CREATE TABLE IF NOT EXISTS readings( \
		route_id INTEGER, \
		humidity INTEGER, \
		temperature INTEGER, \
		lux INTEGER, \
		create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")

	cur.close()

setupDB()
conn.close()







