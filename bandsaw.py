import pymysql
from flask import Flask, request, redirect, url_for, render_template, abort, make_response, g, jsonify
from config import config

class BandsawFrontend:
    def __init__(self):
        self.app = Flask(__name__, static_url_path='/static')

    def register(self):
        @self.app.before_request
        def before_request_handler():
            g.db = pymysql.connect(
                host=config['db-server'],
                user=config['db-username'],
                password=config['db-password'],
                database=config['db-database'],
                autocommit=True
            )

        @self.app.route('/api/attach/<eid>/<aid>', methods=['GET'])
        def attach_api(eid, aid):
            dates = g.db.cursor()
            dates.execute("""
                SELECT datein, dateout FROM events WHERE id = %s
            """, (eid))

            moments = dates.fetchone()

            cursor = g.db.cursor()
            cursor.execute("""
                INSERT INTO event_plays (event, artist, showstart, showend) VALUES (%s, %s, %s, %s)
            """, (eid, aid, moments[0], moments[1]))

            return jsonify({})

        @self.app.route('/api/artists', methods=['GET'])
        def artists_api():
            terms = request.args['term']

            cursor = g.db.cursor()
            cursor.execute("""
                SELECT id, name
                FROM artists
                WHERE name LIKE %s
                ORDER BY name
            """, '%' + terms + '%')

            artists = []

            data = cursor.fetchall()
            for row in data:
                artists.append({
                    'value': row[0],
                    'label': row[1],
                })

            return jsonify(artists)

        @self.app.route('/api/attends/<eid>', methods=['GET'])
        def attends_api(eid):
            cursor = g.db.cursor()
            cursor.execute("""
                SELECT a.id, a.name
                FROM artists a, event_plays e
                WHERE e.artist = a.id
                  AND e.event = %s
            """, eid)

            artists = []

            data = cursor.fetchall()
            for row in data:
                artists.append({
                    'value': row[0],
                    'label': row[1],
                })

            return jsonify(artists)

        @self.app.route('/users/<uid>/<name>', methods=['GET'])
        def user(uid, name):
            cursor = g.db.cursor()

            cursor.execute("""
                SELECT e.name, e.location, a.name, ep.location, es.name,
                       e.location, e.datein, ep.showstart, ep.showend, et.name
                  FROM events e, artists a, event_types et, event_plays ep
                  LEFT JOIN event_shows es ON (es.id = ep.showtype)
                 WHERE ep.artist = a.id
                   AND e.id = ep.event
                   AND et.id = e.type
              ORDER BY e.datein ASC, ep.showstart ASC
            """)

            data = cursor.fetchall()
            event = None
            year = 0
            artists = {}
            contents = {
                'evlist': [],
                'stats': {'events': 0, 'artists': 0},
            }

            for row in data:
                if row[0] != event:
                    event = row[0]
                    contents['stats']['events'] += 1
                    contents['evlist'].append({
                        'name': row[0],
                        'location': row[5],
                        'shows': [],
                        'type': row[9],

                    })

                artists[row[2]] = True

                rlist = contents['evlist'][len(contents['evlist']) - 1]
                rlist['shows'].append({
                    'artist': row[2],
                    'location': row[3],
                    'type': row[4],
                    'start': '%02d:%02d' % (row[7].hour, row[7].minute),
                    'end': '%02d:%02d' % (row[8].hour, row[8].minute),
                })

            contents['stats']['artists'] = len(artists)
            g.db.commit()

            return render_template("user.html", **contents)

        @self.app.route('/', methods=['GET'])
        def homepage():

            return render_template("homepage.html")

        @self.app.route('/users', methods=['GET'])
        def users():
            cursor = g.db.cursor()
            cursor.execute("""SELECT id, username, realname FROM users""")
            users = []

            data = cursor.fetchall()
            for row in data:
                users.append({
                    'uid': row[0],
                    'username': row[1],
                    'realname': row[2],
                })

            length = len(users)

            return render_template("users.html", users=users, length=length)

        @self.app.route('/artists', methods=['GET'])
        def artists():
            cursor = g.db.cursor()
            cursor.execute("""SELECT id, name FROM artists ORDER BY name""")
            artists = []

            data = cursor.fetchall()
            for row in data:
                artists.append({
                    'aid': row[0],
                    'name': row[1],
                    'prettyname': "xxxx",
                })

            length = len(artists)

            return render_template("artists.html", artists=artists, length=length)

        @self.app.route('/artists/create', methods=['GET', 'POST'])
        def artists_create():
            content = {
                'added': False,
                'error': False,
            }

            if request.method == 'POST':
                cursor = g.db.cursor()
                content['name'] = request.form['name']

                try:
                    cursor.execute("INSERT INTO artists (name) VALUES (%s)", (request.form['name']))
                    content['added'] = True

                except pymysql.err.IntegrityError:
                    content['error'] = "Cet artiste existe déjà"


            return render_template("artists_create.html", **content)

        @self.app.route('/events', methods=['GET'])
        def events():
            cursor = g.db.cursor()
            cursor.execute("""
                SELECT e.id, e.name, t.name, datein, dateout, location
                FROM events e
                LEFT JOIN event_types t ON (t.id = e.type)
                ORDER BY datein
            """)
            events = []

            data = cursor.fetchall()
            for row in data:
                events.append({
                    'eid': row[0],
                    'name': row[1],
                    'type': row[2],
                    'start': row[3],
                    'end': row[4],
                    'location': row[5],
                    'prettyname': 'xxxx',
                })

            length = len(events)

            return render_template("events.html", events=events, length=length)

        @self.app.route('/events/create', methods=['GET', 'POST'])
        def events_create():
            content = {
                'added': False,
                'error': False,
                'types': {},
            }

            cursor = g.db.cursor()
            cursor.execute("SELECT id, name FROM event_types ORDER BY id DESC")
            data = cursor.fetchall()

            for row in data:
                content['types'][row[0]] = row[1]

            if request.method == 'POST':
                cursor = g.db.cursor()
                content['name'] = request.form['name']

                try:
                    cursor.execute("""
                        INSERT INTO events (name, type, location) VALUES (%s, %s, %s)

                    """, (request.form['name'], request.form['type'], request.form['location']))

                    content['added'] = True

                except pymysql.err.IntegrityError:
                    content['error'] = "Cet évènement existe déjà"
                    return render_template("events_create.html", **content)

                return redirect("/event/%s/new" % cursor.lastrowid)

            return render_template("events_create.html", **content)

        @self.app.route('/event/<id>/<name>', methods=['GET', 'POST'])
        def events_details(id, name):
            content = {
                'added': False,
                'error': False,
                'types': {},
            }

            cursor = g.db.cursor()
            cursor.execute("SELECT id, name FROM event_types ORDER BY id DESC")
            data = cursor.fetchall()

            for row in data:
                content['types'][row[0]] = row[1]

            cursor = g.db.cursor()
            cursor.execute("""
                SELECT e.id, e.name, t.id, t.name, datein, dateout, location
                FROM events e
                LEFT JOIN event_types t ON (t.id = e.type)
                WHERE e.id = %s
            """, id)

            data = cursor.fetchone()
            print(data)

            content['id'] = data[0]
            content['name'] = data[1]
            content['type'] = data[2]
            content['datein'] = data[4]
            content['dateout'] = data[5]
            content['location'] = data[6]

            if request.method == 'POST':
                cursor = g.db.cursor()
                content['name'] = request.form['name']

                cursor.execute("""
                    UPDATE events SET name = %s, type = %s, location = %s, datein = %s, dateout = %s
                    WHERE id = %s

                """, (
                    request.form['name'],
                    request.form['type'],
                    request.form['location'],
                    request.form['datein'],
                    request.form['dateout'],
                    id)
                )

                return redirect("/event/%s/updated" % id)


            return render_template("events_details.html", **content)

        @self.app.route('/summary/<uid>/<year>', methods=['GET'])
        def summary(uid, year):
            cursor = g.db.cursor()

            cursor.execute("""
                SELECT e.name, e.location, a.name, ep.location, es.name,
                       e.location, e.datein, ep.showstart, ep.showend, et.name
                  FROM events e, artists a, event_types et, event_plays ep
                  LEFT JOIN event_shows es ON (es.id = ep.showtype)
                 WHERE ep.artist = a.id
                   AND e.id = ep.event
                   AND et.id = e.type
                   AND YEAR(e.datein) = %s
              ORDER BY e.datein ASC, ep.showstart ASC
            """, (year))

            data = cursor.fetchall()
            event = None
            artists = {}
            contents = {
                'year': year,
                'evlist': [],
                'stats': {
                    'types': {},
                    'artists': [],
                },
            }

            for row in data:
                print(row)

                if row[0] != event:
                    event = row[0]
                    if row[9] not in contents['stats']['types']:
                        contents['stats']['types'][row[9]] = []

                    contents['stats']['types'][row[9]].append(event)
                    contents['evlist'].append({
                        'name': row[0],
                        'location': row[5],
                        'shows': [],
                        'type': row[9],

                    })

                artists[row[2]] = True

            contents['stats']['types']['Artiste'] = list(artists.keys())
            contents['stats']['types']['Artiste'].sort()

            print(contents)

            return render_template("summary.html", **contents)
    def start(self):
        self.app.run(host="0.0.0.0", port=8001, debug=True, threaded=True)

if __name__ == '__main__':
    bandsaw = BandsawFrontend()
    bandsaw.register()
    bandsaw.start()
