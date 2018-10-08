from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, Response, g
import os
import requests
import sqlite3
import io
import matplotlib.pyplot as plt
import base64
import re
import random
import json_to_sql

app = Flask(__name__)

'''
Config SQLITE3 for local Sqlite3 db
'''

DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def plot_reading(route_id, datatype):
	db = get_db()
	cur = db.cursor()

	cur.execute("SELECT {dt} , create_date FROM readings WHERE route_id = (?) ORDER BY create_date ASC;".format(dt=datatype), (route_id, ))
	readings = cur.fetchall()
	x = []
	y = []

	for reading in readings:
		x += [reading[1]]
		y += [reading[0]]

	plt.plot(x, y)
	plt.xlabel("Date")
	plt.ylabel(datatype.capitalize())

	fig = plt.gcf()
	img = io.BytesIO()
	fig.canvas.print_png(img)
	img.seek(0)
	plt.close()
	plot_url = base64.b64encode(img.getvalue()).decode('ascii')
	img.close()

	return plot_url


@app.route('/product/<int:id>', methods=['GET', 'POST'])
def product(id):

	try:

		json_to_sql.add_nfc_to_product(id)
	except:
		print("Failed to connect to backend")

	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	cur.execute("SELECT * FROM nfc WHERE product_id = (?) ORDER BY scan_date ASC;", (id, ))
	readings = cur.fetchall()

	coords = []

	for reading in readings:
		lat = reading['lat']
		lon = reading['lon']
		coord = [lat, lon]
		coords.append(coord)

	

	return render_template('product.html', readings = readings, coords=coords)

@app.route('/plot/<int:id>', methods=['GET', 'POST'])
def plot(id):

	if request.method == 'POST':

		if 'refresh_route' in request.form:

			success = generate_iot_readings(id)
			if success:
				flash('Refreshed IoT readings', 'success')
				return redirect(url_for('plot', id=id))
			else:
				flash('Refresh failed', 'danger')
				return redirect(url_for('plot', id=id))



		if 'delete_reading' in request.form:

			rowid = request.form['delete_reading']
			remove_reading(rowid)
			flash('Reading removed', 'success')
			return redirect(url_for('plot', id=id))

		elif 'submit_reading' in request.form:
			if request.form["submit_reading"] == "Add Reading":
				temperature = request.form["temperature"]
				humidity = request.form["humidity"]
				lux = request.form["lux"]
				add_reading(id, temperature, humidity, lux)
				flash('Reading added', 'success')
				return redirect(url_for('plot', id=id))

		elif 'update_route' in request.form:
			if 'route_select' in request.form:
				select = request.form['route_select']

				if is_int(select):
					select = int(select)

				elif select == "None":
					select = None

				update_next_route(id, select)

	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	cur.execute("SELECT *, rowid FROM readings WHERE route_id = (?) ORDER BY create_date ASC;", (id, ))
	readings = cur.fetchall()

	cur.execute("SELECT * FROM route WHERE route_id = (?);", (id, ))
	route = cur.fetchone()


	cur.execute("SELECT location_name, lat, lon FROM location WHERE location_id = (?)", (route['src_id'], ))
	source = cur.fetchone()
	cur.execute("SELECT location_name, lat, lon FROM location WHERE location_id = (?)", (route['dest_id'], ))	
	dest = cur.fetchone()

	
	

	src_coord = []
	dest_coord = []

	if source['lat'] == None or source['lon'] == None:
		src_query = re.sub(' ', '+', source[0].lower()) + "+,usa"
		response = requests.get("https://nominatim.openstreetmap.org/?q={query}&format=json&limit=1".format(query=src_query)).json()
		src_coord = [response[0]['lat'], response[0]['lon']]
		cur.execute("UPDATE location SET lat = ?, lon = ? WHERE location_id = ?", (src_coord[0], src_coord[1], route['src_id']))
		db.commit()
	else:
		src_coord = [source['lat'], source['lon']]

	if dest['lat'] == None or dest['lon'] == None:
		dest_query = re.sub(' ', '+', dest[0].lower()) + "+,usa"
		response = requests.get("https://nominatim.openstreetmap.org/?q={query}&format=json&limit=1".format(query=dest_query)).json()
		dest_coord = [response[0]['lat'], response[0]['lon']]
		cur.execute("UPDATE location SET lat = ?, lon = ? WHERE location_id = ?", (dest_coord[0], dest_coord[1], route['dest_id']))
		db.commit()
	else:
		dest_coord = [dest['lat'], dest['lon']]

	bounds = [src_coord, dest_coord]


	cur.execute("SELECT route_id FROM route;")
	route_ids = cur.fetchall()


	cur.close()


	plot_urls = [plot_reading(id, 'temperature'), plot_reading(id, 'humidity'), plot_reading(id, 'lux')]
	return render_template('plot.html', plot_urls=plot_urls, id=id, readings = readings, bounds = bounds, route=route, src=source['location_name'], dest=dest['location_name'], route_ids=route_ids)

def update_next_route(route_id, next_route):
	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	cur.execute("UPDATE route SET next_route = ? WHERE route_id = ?;", (next_route, route_id))
	db.commit()
	cur.close()


def add_product(product_id, product_type, start_route):

	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	if len(product_type) < 3:
		flash('Product type must be greater than 3 characters', 'danger')
		return redirect(url_for('index'))

	if len(start_route) > 0:
		try:
			start_route = int(start_route)
		except ValueError:
			flash('Start Route ID must be a number', 'danger')
			return redirect(url_for('index'))
	else:
		start_route = None


	if len(product_id) == 0:
		cur.execute("INSERT INTO product(product_type, start_route) VALUES (?, ?);", (product_type, start_route))

	else:
		cur.execute("SELECT EXISTS(SELECT 1 FROM product WHERE product_id = ?)", (product_id, ))
		id_exists = cur.fetchone()
		if id_exists[0]:
			flash('Product with that ID already exists', 'danger')
			return redirect(url_for('index'))

		cur.execute("INSERT INTO product(product_id, product_type, start_route) VALUES (?, ?, ?);", (product_id, product_type, start_route))
	
	cur.close()
	db.commit()

	flash('New product added', 'success')
	return redirect(url_for('index'))

def remove_product(product_id):
	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()
	cur.execute("DELETE FROM product WHERE product_id = ?;", (product_id, ))
	
	db.commit()
	cur.close()
	flash('Product {id} deleted'.format(id=product_id), 'success')
	return redirect(url_for('index'))


def add_route(route_id, src_id, dest_id, next_route):

	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	if len(route_id) > 0:
		try:
			route_id = int(route_id)
		except ValueError:
			flash('Route ID must be a number', 'danger')
			return redirect(url_for('index'))

	if len(next_route) > 0:
		try:
			next_route = int(next_route)
		except ValueError:
			flash('Next Route ID must be a number', 'danger')
			return redirect(url_for('index'))
	else:
		next_route = None

	if len(src_id) < 3 or len(dest_id) < 3:
		flash('Source or Destination must be greater than 3 characters', 'danger')
		return redirect(url_for('index'))
	else:
		src_id = get_location(src_id)
		dest_id = get_location(dest_id)

	if len(route_id) == 0:
		print(src_id, dest_id, next_route)
		cur.execute("INSERT INTO route(src_id, dest_id, next_route) VALUES (?, ?, ?);", (src_id, dest_id, next_route))

	else:
		cur.execute("SELECT EXISTS(SELECT 1 FROM route WHERE route_id = ?)", (route_id, ))
		id_exists = cur.fetchone()
		if id_exists[0]:
			flash('Route with that ID already exists', 'danger')
			return redirect(url_for('index'))

		cur.execute("INSERT INTO route(route_id, src_id, dest_id, next_route) VALUES (?, ?, ?, ?);", (route_id, src_id, dest_id, next_route))

	db.commit()
	cur.close()
	flash('New route added', 'success')
	return redirect(url_for('index'))

def remove_route(route_id):
	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	cur.execute("SELECT rowid FROM readings WHERE route_id = ?;", (route_id, ))
	readings = cur.fetchall()

	for reading in readings:
		remove_reading(reading[0])

	cur.execute("DELETE FROM route WHERE route_id = ?;", (route_id, ))
	
	db.commit()
	cur.close()
	

def add_reading(route_id, temperature, humidity, lux):
	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	if is_int(temperature):
		temperature = int(temperature)
	elif len(temperature) == 0:
		temperature = random.randint(40, 120)
	else:
		flash('Temperature must be a number', 'danger')
		return None

	if is_int(humidity):
		humidity = int(humidity)
	elif len(humidity) == 0:
		humidity = random.randint(30, 70)
	else:
		flash('Humidity must be a number', 'danger')
		return None

	if is_int(lux):
		lux = int(lux)
	elif len(lux) == 0:
		lux = random.randint(60, 130)
	else:
		flash('Lux must be a number', 'danger')
		return None

	cur.execute("INSERT INTO readings(route_id, temperature, humidity, lux) VALUES(?, ?, ?, ?);", (route_id, temperature, humidity, lux))

	db.commit()
	cur.close()


def is_int(req):
	if len(req) > 0:
		try:
			int(req)
			return True
		except ValueError:
			pass
	return False


def remove_reading_from_plot(rowid):
	remove_reading(rowid)
	flash('Reading removed', 'success')


def remove_reading(rowid):

	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	cur.execute("DELETE FROM readings WHERE rowid = ?;", (rowid, ))

	db.commit()
	cur.close()

def get_location(name):
	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	cur.execute("SELECT location_id FROM location WHERE location_name = ?;", (name, ))


	location_id = cur.fetchone()
	if location_id:
		return location_id[0]
	else:
		cur.execute("INSERT INTO location(location_name) VALUES(?);", (name, ))
		db.commit()
		return cur.lastrowid

	cur.close()

@app.route('/generate_iot_readings/<int:id>')
def generate_iot_readings(id):

	try:
		json_to_sql.add_readings_to_route(id)
	except:
		print("Cannot connect to database")

	return "Success"





@app.route('/', methods=['GET', 'POST'])
def index():

	if request.method == 'POST':

		if 'delete_product' in request.form:
			delete_product_id = request.form['delete_product']
			if delete_product_id:
				remove_product(delete_product_id)

		if 'delete_route' in request.form:
			delete_route_id = request.form['delete_route']
			if delete_route_id:
				remove_route(delete_route_id)
				flash('Route {id} and associated readings deleted'.format(id=delete_route_id), 'success')
				return redirect(url_for('index'))

		elif 'submit_button' in request.form:
			
			if request.form['submit_button'] == 'Add Product':
				
				product_id = request.form["product_id"]
				product_type = request.form["product_type"]
				start_route = request.form["start_route"]
				add_product(product_id, product_type, start_route)


			elif request.form['submit_button'] == 'Add Route':

				route_id = request.form["route_id"]
				src_id = request.form["src_id"]
				dest_id = request.form["dest_id"]
				next_route = request.form["next_route"]
				add_route(route_id, src_id, dest_id, next_route)


	db = get_db()
	db.row_factory = sqlite3.Row
	cur = db.cursor()

	
	cur.execute("SELECT * FROM product;")
	products = cur.fetchall()

	cur.execute("SELECT * FROM route;")
	routes = cur.fetchall()

	cur.execute("SELECT * FROM location;")
	locations = cur.fetchall()

	return render_template('home.html', products = products, routes = routes, locations = locations)


if __name__ == '__main__':
	app.secret_key='secret'
	app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '8080')), debug=True)

