from flask import Flask, render_template, jsonify
from scrape import scrape_api
import models as db
from sqlalchemy import distinct, func, desc, and_, case
from sqlalchemy.sql.functions import coalesce
from sqlalchemy.orm import aliased
from random import randint

"""
init Flask
"""
app = Flask(__name__)
app.register_blueprint(scrape_api, url_prefix='/scrape')

"""
endpoint defs
"""
"""
@app.route('/')
def hello_world():
    # return q[0].name
    return 'Hello World!'
"""
"""
@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)
"""

@app.route('/index/')
@app.route('/home/')
@app.route('/')
def index(): 

    featured_games = "Country Year"
    featured_sports = "Sport"
    featured_countries = "Country"
    featured_athletes_pic = "Athlete Portrait"

    return render_template('index.html', featured_games=featured_games,
            featured_sports=featured_sports,
            featured_countries=featured_countries,
            featured_athletes_pic=featured_athletes_pic,
            athlete_name="Michael Phelps", athlete_country="USA",
            num_gold=0, num_silver=0, num_bronze=0)

@app.route('/games/')
def games():

    session = db.loadSession()

    # random_game_banner - a random game banner
    random_game_banner = None

    # all_games - [(host_country_banner, "city_name game_year")]
    all_games = []

    all_games_query = session.query(db.City.name, db.Olympics.year)\
                    .select_from(db.Olympics)\
                    .join(db.City)\
                    .all()

    for r in all_games_query:
        host_country_banner = None
        all_games += (host_country_banner, str(r[0]) + " " + str(r[1]))

    return render_template('games.html',
                            random_game_banner = random_game_banner,
                            all_games = all_games)

@app.route('/games/<int:game_id>')
def games_id(game_id = None):
    
    session = db.loadSession()

    # random_game_banner - a random game banner
    random_game_banner = None

    # host_country_banner - the host country banner
    host_country_banner = None

    # host_city - the hosting city
    host_city = ""

    # year - the game year
    year = ""

    # top_athletes - [("first_name last_name", "rep_country", total_g, total_s, total_b)]
    top_athletes = []

    # top_countries - [("country_name", c_total_g, c_total_s, c_total_b)]
    top_countries = []

    # all_events - [(event_id, sport_id, "name")]
    all_events = []

    # all_countries - [(country_id, "name", NOC)]
    all_countries = []

    host_query = session.query(db.City.name, db.Olympics.year)\
                    .select_from(db.Olympics)\
                    .filter(game_id == db.Olympics.id)\
                    .join(db.City)\
                    .all()

    host_city = host_query[0][0]
    year = host_query[0][1]

    athletes_query = session.query(distinct(db.Athlete.id).label('athlete_id'))\
                            .select_from(db.Athlete)\
                            .join(db.Medal)\
                            .filter(game_id == db.Medal.olympic_id)\
                            .subquery()

    total_athletes_g = session.query(athletes_query.c.athlete_id.label('id'), func.count(db.Medal.rank).label('num_gold'))\
                            .select_from(db.Medal)\
                            .filter(db.Medal.rank == "Gold")\
                            .filter(game_id == db.Medal.olympic_id)\
                            .join(athletes_query, db.Medal.athlete_id == athletes_query.c.athlete_id)\
                            .group_by(athletes_query.c.athlete_id)\
                            .subquery()

    total_athletes_s = session.query(athletes_query.c.athlete_id.label('id'), func.count(db.Medal.rank).label('num_silver'))\
                            .select_from(db.Medal)\
                            .filter(db.Medal.rank == "Silver")\
                            .filter(game_id == db.Medal.olympic_id)\
                            .join(athletes_query, db.Medal.athlete_id == athletes_query.c.athlete_id)\
                            .group_by(athletes_query.c.athlete_id)\
                            .subquery()

    total_athletes_b = session.query(athletes_query.c.athlete_id.label('id'), func.count(db.Medal.rank).label('num_bronze'))\
                            .select_from(db.Medal)\
                            .filter(db.Medal.rank == "Bronze")\
                            .filter(game_id == db.Medal.olympic_id)\
                            .join(athletes_query, db.Medal.athlete_id == athletes_query.c.athlete_id)\
                            .group_by(athletes_query.c.athlete_id)\
                            .subquery()

    top_athletes_query = session.query(distinct(db.Athlete.id), db.Athlete.first_name, db.Athlete.last_name, db.Country.name,
                                        coalesce(total_athletes_g.c.num_gold, 0),
                                        coalesce(total_athletes_s.c.num_silver, 0),
                                        coalesce(total_athletes_b.c.num_bronze, 0))\
                                .select_from(db.Athlete)\
                                .join(db.Medal)\
                                .filter(game_id == db.Medal.olympic_id)\
                                .join(db.Country)\
                                .outerjoin(total_athletes_g, and_(db.Athlete.id == total_athletes_g.c.id))\
                                .outerjoin(total_athletes_s, and_(db.Athlete.id == total_athletes_s.c.id))\
                                .outerjoin(total_athletes_b, and_(db.Athlete.id == total_athletes_b.c.id))\
                                .order_by(coalesce(total_athletes_g.c.num_gold, 0).desc())\
                                .limit(3)\
                                .all()

    for r in top_athletes_query:
        top_athletes += r[1:]

    
    countries_query = session.query(distinct(db.Country.id).label('country_id'))\
                            .select_from(db.Country)\
                            .join(db.Medal)\
                            .filter(game_id == db.Medal.olympic_id)\
                            .subquery()

    medals_query = session.query(db.Medal.event_id.label('event_id'), db.Medal.country_id.label('country_id'), 
                                    db.Medal.rank.label('rank'), db.Medal.olympic_id.label('olympic_id'))\
                            .select_from(db.Medal)\
                            .group_by(db.Medal.event_id, db.Medal.rank, db.Medal.country_id, db.Medal.olympic_id)\
                            .subquery()

    total_countries_g = session.query(countries_query.c.country_id.label('id'),
                                        func.count(medals_query.c.rank).label('num_gold'))\
                            .select_from(medals_query)\
                            .filter(medals_query.c.rank == "Gold")\
                            .filter(game_id == medals_query.c.olympic_id)\
                            .join(countries_query, medals_query.c.country_id == countries_query.c.country_id)\
                            .group_by(countries_query.c.country_id)\
                            .subquery()

    total_countries_s = session.query(countries_query.c.country_id.label('id'),
                                        func.count(medals_query.c.rank).label('num_silver'))\
                            .select_from(medals_query)\
                            .filter(medals_query.c.rank == "Silver")\
                            .filter(game_id == medals_query.c.olympic_id)\
                            .join(countries_query, medals_query.c.country_id == countries_query.c.country_id)\
                            .group_by(countries_query.c.country_id)\
                            .subquery()

    total_countries_b = session.query(countries_query.c.country_id.label('id'),
                                        func.count(medals_query.c.rank).label('num_bronze'))\
                            .select_from(medals_query)\
                            .filter(medals_query.c.rank == "Bronze")\
                            .filter(game_id == medals_query.c.olympic_id)\
                            .join(countries_query, medals_query.c.country_id == countries_query.c.country_id)\
                            .group_by(countries_query.c.country_id)\
                            .subquery()

    top_countries_query = session.query(distinct(db.Country.id), db.Country.name,
                                        coalesce(total_countries_g.c.num_gold, 0),
                                        coalesce(total_countries_s.c.num_silver, 0),
                                        coalesce(total_countries_b.c.num_bronze, 0))\
                                .select_from(db.Country)\
                                .join(db.Medal)\
                                .filter(game_id == db.Medal.olympic_id)\
                                .outerjoin(total_countries_g, and_(db.Country.id == total_countries_g.c.id))\
                                .outerjoin(total_countries_s, and_(db.Country.id == total_countries_s.c.id))\
                                .outerjoin(total_countries_b, and_(db.Country.id == total_countries_b.c.id))\
                                .order_by(coalesce(total_countries_g.c.num_gold, 0).desc())\
                                .limit(3)\
                                .all()
    
    for r in top_countries_query:
        top_countries += r[1:]

    all_events = session.query(distinct(db.Event.id), db.Event.sport_id, db.Event.name)\
                    .select_from(db.Event)\
                    .join(db.Medal)\
                    .join(db.Olympics)\
                    .filter(game_id == db.Olympics.id)\
                    .all()

    all_countries = session.query(distinct(db.Country.id), db.Country.name, db.Country.noc)\
                        .select_from(db.Country)\
                        .join(db.Medal)\
                        .join(db.Olympics)\
                        .filter(game_id == db.Olympics.id)\
                        .all()

    return render_template('games.html',
                            random_game_banner = random_game_banner,
                            host_country_banner = host_country_banner,
                            host_city = host_city,
                            year = year,
                            top_athletes = top_athletes,
                            top_countries = top_countries,
                            all_events = all_events,
                            all_countries = all_countries)

@app.route('/sports/')
def sports():

    session = db.loadSession()

    # stock sports banner
    stock_sports_banner = None 

    # featured sports - [(id, "name")]
    featured_sports = [] 

    # sports - [(id, "name")]
    sports = session.query(db.Sport.id, db.Sport.name)\
                            .select_from(db.Sport)\
                            .all()
    
    while len(featured_sports) < 3:
        sport = sports[randint(0, len(sports)) - 1]
        if sport not in featured_sports:
            featured_sports.append(sport)

    return render_template('sports.html', 
                            stock_sports_banner = stock_sports_banner,
                            featured_sports = featured_sports,
                            sports = sports)

@app.route('/sports/<int:id>')
def sports_id(sport_id = None):

    session = db.loadSession()

    # sports banner
    sports_banner = None

    # top medalists - [("name", "results", "year")]
    top_medalists = session.query(db.Athlete.first_name, db.Athlete.last_name, func.count(db.Medal.rank))\
                            .select_from(db.Sport)\
                            .filter(db.Sport.id == sport_id)\
                            .join(db.Event)\
                            .join(db.Medal)\
                            .join(db.Athlete)\
                            .group_by(db.Athlete.id)\
                            .order_by(func.count(db.Medal.rank).desc())\
                            .all()

    return render_template('sports.html',
                            sports_banner = sports_banner,
                            top_medalists = top_medalists)

@app.route('/events/')
def events():
    
    session = db.loadSession()

    # stock events banner
    stock_events_banner = None

    # featured events - [(img, "name")]
    featured_events = []

    events = session.query(db.Event.name)\
                            .select_from(db.Event)\
                            .all()
    
    while len(featured_events) < 3:
        event = events[randint(0, len(events)) - 1]
        if (None, event) not in featured_events:
            featured_events.append((None, event))

    return render_template('events.html',
                            stock_events_banner = stock_events_banner,
                            featured_events = featured_events)

@app.route('/events/<int:event_id>')
def events_id(event_id = None):
    
    session = db.loadSession()

    # stock events banner
    stock_events_banner = None
    
    # medalists [("city + year", (gold athlete photo, "name"), 
    #                            (silver athlete photo, "name"),
    #                            (bronze athlete photo, "name))]

    gold_medalists = session.query(db.Athlete.first_name.label("first_name"),
                                    db.Athlete.last_name.label("last_name"),
                                    db.Medal.olympic_id.label("olympic_id"))\
                                    .select_from(db.Medal)\
                                    .filter(db.Medal.event_id == event_id)\
                                    .filter(db.Medal.rank == "Gold")\
                                    .join(db.Athlete)\
                                    .subquery()
    
    silver_medalists = session.query(db.Athlete.first_name.label("first_name"),
                                    db.Athlete.last_name.label("last_name"),
                                    db.Medal.olympic_id.label("olympic_id"))\
                                    .select_from(db.Medal)\
                                    .filter(db.Medal.event_id == event_id)\
                                    .filter(db.Medal.rank == "Silver")\
                                    .join(db.Athlete)\
                                    .subquery()

    bronze_medalists = session.query(db.Athlete.first_name.label("first_name"),
                                    db.Athlete.last_name.label("last_name"),
                                    db.Medal.olympic_id.label("olympic_id"))\
                                    .select_from(db.Medal)\
                                    .filter(db.Medal.event_id == event_id)\
                                    .filter(db.Medal.rank == "Bronze")\
                                    .join(db.Athlete)\
                                    .subquery()

    medalists_query = session.query(db.City.name, db.Olympics.year, 
                                    gold_medalists.c.first_name,
                                    gold_medalists.c.last_name,
                                    silver_medalists.c.first_name,
                                    silver_medalists.c.last_name,
                                    bronze_medalists.c.first_name,
                                    bronze_medalists.c.last_name)\
                                    .select_from(db.City)\
                                    .join(db.Olympics)\
                                    .join(gold_medalists)\
                                    .join(silver_medalists)\
                                    .join(bronze_medalists)\
                                    .all()
    medalists = []
    for game in medalists_query:
        medalists.append((str(game[0]) + " " + str(game[1]), 
                            (None, str(game[2]) + " " + str(game[3])),
                            (None, str(game[4]) + " " + str(game[5])),
                            (None, str(game[6]) + " " + str(game[7]))))

    return render_template('events.html',
                            stock_events_banner = stock_events_banner,
                            medalists = medalists)

@app.route('/athletes/', methods = ['GET'])
def athletes_featured_athletes():
    
    session = db.loadSession()

    result = session.query(
                db.Athlete.id,
                db.Athlete.first_name + ' ' + db.Athlete.last_name,
                db.Country.id,
                db.Country.name,
                db.Sport.id,
                db.Sport.name,
                db.Olympics.id,
                db.Olympics.year,
                func.count(db.Medal.id).label('total_medals')
            )\
            .select_from(db.Athlete).join(db.Medal)\
            .join(db.Country)\
            .join(db.Event)\
            .join(db.Sport)\
            .join(db.Olympics)\
            .group_by(db.Athlete.id,
                db.Athlete.first_name + ' ' + db.Athlete.last_name,
                db.Country.id,
                db.Country.name,
                db.Sport.id,
                db.Sport.name,
                db.Olympics.id,
                db.Olympics.year,).limit(3).all()
    
    # Make an entry for every athlete in a dictionary and
    #   update their data when their row repeats
    all_athletes_dict=dict()
    for row in result:
        athlete_id = row[0]

        if athlete_id not in all_athletes_dict:
            all_athletes_dict[athlete_id] = {
                'id':athlete_id,
                'name':row[1],
                'country_id': row[2],
                'country': row[3],
                'sports':[(row[4], row[5])],
                'years':[(row[6],row[7])],
                'total_medals':row[8],
                'latest_year':row[7]}
        else:
            athlete = all_athletes_dict[athlete_id]
            
            if athlete['latest_year'] >= row[7]:
                athlete['latest_year'] = row[7]
                athlete['country_id'] = row[2]
                athlete['country'] = row[3]
                
            athlete['sports'] += [(row[4],row[5])]
            athlete['years'] += [(row[6],row[7])]

    return render_template('athletes.html')#, athletes=all_athletes_dict.values())

@app.route('/athletes/<int:athlete_id>', methods = ['GET'])
def get_athlete_by_id(athlete_id):

    session = db.loadSession()

    # Make a subquery to get the athlete's latest country represented
    get_athlete_sub = session.query(
        db.Medal.athlete_id,
        db.Country.id,
        db.Country.name
        )\
        .select_from(db.Medal)\
        .join(db.Country)\
        .join(db.Olympics)\
        .filter(db.Medal.athlete_id==athlete_id)\
        .order_by(db.Olympics.year.desc())\
        .limit(1)\
        .subquery()

    # Make a query to get the athlete's data
    athlete_data = session.query(
                db.Athlete.id,
                db.Athlete.first_name,
                db.Athlete.last_name,
                db.Athlete.gender,
                get_athlete_sub.c.id,
                get_athlete_sub.c.name,
                db.Sport.id,
                db.Sport.name,
                db.Olympics.id,
                db.Olympics.year,
                func.count(db.Medal.id))\
            .select_from(db.Athlete)\
            .join(db.Medal)\
            .join(get_athlete_sub, db.Athlete.id==get_athlete_sub.c.athlete_id)\
            .join(db.Event)\
            .join(db.Sport)\
            .join(db.Olympics)\
            .group_by(
                db.Athlete.id,
                db.Athlete.first_name,
                db.Athlete.last_name,
                db.Athlete.gender,
                get_athlete_sub.c.id,
                get_athlete_sub.c.name,
                db.Sport.id,
                db.Sport.name,
                db.Olympics.id,
                db.Olympics.year)\
            .all()
    
    # Make a query to get the top events for the athlete
    top_events_query = session.query(
            db.Event.id,
            db.Event.name,
            db.Sport.id,
            db.Sport.name,
            func.sum(case([(db.Medal.rank=='Gold', 1)], else_=0)).label('gold'), func.sum(case([(db.Medal.rank=='Silver', 1)], else_=0)).label('silver'), func.sum(case([(db.Medal.rank=='Bronze', 1)], else_=0)).label('bronze')
        )\
        .select_from(db.Event)\
        .join(db.Medal)\
        .join(db.Sport)\
        .filter(db.Medal.athlete_id==athlete_id)\
        .group_by(
            db.Event.id,
            db.Event.name,
            db.Sport.id,
            db.Sport.name)\
        .order_by('gold', 'silver', 'bronze')\
        .limit(3)\
        .all()
    
    # Put the results in a list of dictionaries
    top_events_list = [{
        'sport_id':r[2],
        'sport': r[3],
        'event_id':r[0],
        'event': r[1],
        'gold': r[4],
        'silver': r[5],
        'bronze': r[6]
        } for r in top_events_query]
    
    # Make a query to get the games participated for the athlete
    games_part = session.query(
            db.Olympics.id,
            db.Olympics.year,
            db.Country.id,
            db.Country.name,
            db.Event.id,
            db.Event.name,
            db.Event.id,
            db.Sport.name,
            db.Medal.rank
        )\
        .select_from(db.Olympics)\
        .join(db.Medal)\
        .join(db.Event)\
        .join(db.Sport)\
        .join(db.Country)\
        .filter(db.Medal.athlete_id==athlete_id)\
        .all()

    olympics_dict = dict()
    for row in games_part:
        olympic_year = row[1]
        
        if olympic_year not in olympics_dict:
            olympics_dict[olympic_year] = [{
                'olympic_id': row[0],
                'country_id': row[2],
                'country': row[3],
                'event_id': row[4],
                'event': row[5],
                'sport_id': row[6],
                'sport': row[7],
                'medal': row[8]}]
        else:
            olympics_dict[olympic_year] += ({
                'olympic_id': row[0],
                'country_id': row[2],
                'country': row[3],
                'event_id': row[4],
                'event': row[5],
                'sport_id': row[6],
                'sport': row[7],
                'medal': row[8]},)
    
    athlete_dict = {
        'id': athlete_data[0][0],
        'name': athlete_data[0][1] + ' ' + athlete_data[0][2],
        'gender': athlete_data[0][3],
        'country_repr_id':athlete_data[0][4],
        'country_repr':athlete_data[0][5],
        'sports': list({(r[6],r[7]) for r in athlete_data}),
        'years': [(r[8],r[9]) for r in athlete_data],
        'total_medals':athlete_data[0][10],
        'top_events': top_events_list,
        'games_part': olympics_dict
        }
    

    return str(athlete_dict) #render_template('athletes.html', **athlete_dict)

@app.route('/countries/')
def countries():
    
    session = db.loadSession()

    # stock global banner
    stock_global_banner = None

    # featured countries - [(id, "country name", ["years hosted"], total_medals, num_medalists)] 
    featured_countries = []

    # all_countries - [(id, "name")]
    all_countries = []

    countries = session.query(db.Country.id, db.Country.name,  
                                func.array_agg(distinct(db.Olympics.year)),
                                func.count(db.Medal.id), 
                                func.count(distinct(db.Medal.athlete_id)))\
                                .select_from(db.Country)\
                                .join(db.City)\
                                .join(db.Olympics)\
                                .join(db.Medal)\
                                .group_by(db.Country.name, db.Country.id)\
                                .all()

    while len(featured_countries) < 3:
        country = countries[randint(0, len(countries)) - 1]
        if country not in featured_countries:
            featured_countries.append(country)
    
    for country in countries:
        all_countries.append((country[0], country[1])) 

    return render_template('countries.html',
                            stock_global_banner = stock_global_banner,
                            all_countries = all_countries,
                            featured_countries = featured_countries)

@app.route('/countries/<int:country_id>')
def country_id(country_id):
    
    session = db.loadSession()

    # country banner
    country_banner = None

    # country name
    country_name = session.query(db.Country.name)\
                            .select_from(db.Country)\
                            .filter(db.Country.id == country_id)\
                            .all()

    # total gold medals
    total_gold_medals = session.query(func.sum(case([(db.Medal.rank == 'Gold', 1)], else_=0)), func.count(db.Medal.id))\
                                .select_from(db.Country)\
                                .filter(db.Country.id == country_id)\
                                .join(db.Medal)\
                                .all()


    # total medals overall
    total_medals = total_gold_medals[0][1]

    # total athletes
    total_athletes = session.query(func.count(distinct(db.Medal.athlete_id)))\
                            .select_from(db.Medal)\
                            .filter(db.Medal.country_id == country_id)\
                            .all()
    # years hosted = [year]
    years_hosted = session.query(db.Olympics.year)\
                            .select_from(db.Country)\
                            .filter(db.Country.id == country_id)\
                            .join(db.City)\
                            .join(db.Olympics)\
                            .all()
    
    # top medalists - [(id, "first_name", "last_name", "gender")]
    top_medalists = session.query(db.Athlete.id, db.Athlete.first_name, db.Athlete.last_name, db.Athlete.gender)\
                            .select_from(db.Medal)\
                            .filter(db.Medal.country_id == country_id)\
                            .join(db.Athlete)\
                            .order_by(func.sum(case([(db.Medal.rank == 'Gold', 1)], else_=0)).desc())\
                            .group_by(db.Athlete.id, db.Athlete.first_name, db.Athlete.last_name, db.Athlete.gender)\
                            .all()

    # top years - [(year, [total medals, [("first_name last_name", num_gold, num_silver, num_bronze, num_medals)]])]
    top_years_query = session.query(db.Olympics.year, db.Athlete.first_name, db.Athlete.last_name, 
                                func.sum(case([(db.Medal.rank == 'Gold', 1)], else_=0)),
                                func.sum(case([(db.Medal.rank == 'Silver', 1)], else_=0)),
                                func.sum(case([(db.Medal.rank == 'Bronze', 1)], else_=0)),
                                func.count(1))\
                                .select_from(db.Olympics)\
                                .join(db.Medal)\
                                .join(db.Athlete)\
                                .filter(db.Medal.country_id == country_id)\
                                .group_by(db.Olympics.year, db.Athlete.first_name, db.Athlete.last_name)\
                                .order_by(db.Olympics.year)\
                                .all()

    top = {}
    for athlete in top_years_query:
        if athlete[0] not in top:
            top[athlete[0]] = [0, []]
        top[athlete[0]][1].append(tuple([str(athlete[1]) + " " + str(athlete[2])] + list(athlete[3:])))
        top[athlete[0]][0] += athlete[5]
        
    top_years = list(top.items())
    top_years.sort(key = lambda x : x[1][0], reverse = True)

    # top events - [(event_id, "event_name", total_medals)]
    # frequently has fewer than 3 events in test database
    top_events = session.query(db.Event.id, db.Event.name, func.count(db.Medal.id))\
                        .select_from(db.Medal)\
                        .filter(db.Medal.country_id == country_id)\
                        .join(db.Event)\
                        .order_by(func.count(db.Medal.id).desc())\
                        .group_by(db.Event.id)\
                        .limit(3)\
                        .all()

    return render_template("countries.html",
                            country_banner = country_banner,
                            country_name = country_name,
                            total_gold_medals = total_gold_medals,
                            total_medals = total_medals,
                            total_athletes = total_athletes,
                            years_hosted = years_hosted,
                            top_medalists = top_medalists,
                            top_years = top_years,
                            top_events = top_events)

@app.route('/about/')
def about():
    return render_template('about.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

"""
main
"""
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)
