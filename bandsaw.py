import pymysql
from flask import Flask, request, redirect, url_for, render_template, abort, make_response

class BandsawFrontend:
    def __init__(self):
        self.db = pymysql.connect("127.0.0.1", "", "", "")

        self.app = Flask(__name__, static_url_path='/static')

    def register(self):
        @self.app.route('/', methods=['GET'])
        def homepage():
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

            return render_template("homepage.html", **contents)

    def start(self):
        self.app.run(host="0.0.0.0", port=8001, debug=True, threaded=True)

if __name__ == '__main__':
    bandsaw = BandsawFrontend()
    bandsaw.register()
    bandsaw.start()
