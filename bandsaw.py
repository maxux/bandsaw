import pymysql
from flask import Flask, request, redirect, url_for, render_template, abort, make_response
from config import config

class BandsawFrontend:
    def __init__(self):
        self.db = pymysql.connect(config['db-server'], config['db-username'], config['db-password'], config['db-database'])

        self.app = Flask(__name__, static_url_path='/static')

    def register(self):
        @self.app.route('/users/<uid>/<name>', methods=['GET'])
        def user(uid, name):
            cursor = self.db.cursor()

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
            self.db.commit()

            return render_template("user.html", **contents)

        @self.app.route('/', methods=['GET'])
        def homepage():

            return render_template("homepage.html")

        @self.app.route('/users', methods=['GET'])
        def users():
            cursor = self.db.cursor()
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
            cursor = self.db.cursor()
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

        @self.app.route('/events', methods=['GET'])
        def events():
            cursor = self.db.cursor()
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



    def start(self):
        self.app.run(host="0.0.0.0", port=8001, debug=True, threaded=True)

if __name__ == '__main__':
    bandsaw = BandsawFrontend()
    bandsaw.register()
    bandsaw.start()
