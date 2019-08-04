from flask import Flask, render_template, request, redirect, g, session, url_for
import psycopg2
import json
from datetime import timedelta
import time

app = Flask(__name__)

app.secret_key = '28ANsjwesjCigaXHJNfY6-AS4GglnRkkEFz88uqkMzs'
import os
# app.config.from_object(os.environ['APP_SETTINGS'])

db_user = os.environ.get('CLOUD_SQL_USERNAME')
db_password = os.environ.get('CLOUD_SQL_PASSWORD')
db_name = os.environ.get('CLOUD_SQL_DATABASE_NAME')
db_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
# DATABASE_URL = os.environ.get('DATABASE_URL')

@app.route('/')
def home():
    return render_template('home_copy.html', username=session['username'])


@app.before_request
def before_request():
    # When deployed to App Engine, the `GAE_ENV` environment variable will be
    # set to `standard`
    if os.environ.get('GAE_ENV') == 'standard':
        # If deployed, use the local socket interface for accessing Cloud SQL
        host = '/cloudsql/{}'.format(db_connection_name)
        conn = psycopg2.connect(dbname=db_name, user=db_user,
                                password=db_password, host=host)
    else:
        conn = psycopg2.connect('postgres://postgres:admin@127.0.0.1:5432/weights_psq')

    g.conn = conn
    c = conn.cursor()
    conn.autocommit = True
    g.c = c
    session.permanent = True
    app.permanent_session_lifetime = timedelta(weeks=52)
    if 'username' not in session and request.path != '/login':
        return redirect('/login')


@app.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    c = g.pop('c', None)
    if c is not None:
        c.close()

    conn = g.pop('conn', None)
    if conn is not None:
        conn.close()
    return response


@app.route('/signup', methods=['POST'])
def signup():
    username = session['username']
    weight = request.form['weight']
    date = request.form['date']
    if len(weight) > 1 and len(date) == 10:
        g.c.execute('INSERT INTO weights (date, weight, username) VALUES(%s, %s, %s)', (date, weight, username))
    return redirect('/')


@app.route("/graph")
def graph():
    username = session['username']
    g.c.execute('SELECT date, weight FROM weights WHERE username= %s ORDER BY date', (username,))
    data = g.c.fetchall()
    results = []
    for row in data:
        new_row = []
        new_row.append(row[0].isoformat())
        new_row.append(float(row[1]))
        results.append(new_row)
    print(results)
    return render_template('graph.html', data=json.dumps(results), username=username)


@app.route('/weights.html')
def weight():
    username = session['username']
    g.c.execute('SELECT date, weight FROM weights WHERE username = %s ORDER BY date DESC', (username,))
    weight_date = g.c.fetchall()
    return render_template('weights.html', username=username, weight_date=weight_date)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form['username']
        session['username'] = username
        return redirect('/')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
