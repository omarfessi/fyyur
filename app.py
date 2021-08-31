#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
from operator import ne
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from models import db, Venue, Artist, Show   
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():

  venues = Venue.query.all()

  data = []
  current_time = datetime.now()

  
  locations = set()
  for venue in venues : 
    locations.add((venue.city, venue.state))
  locations = list(locations)

  for location in locations : 
    """ we can have multiple venues in one location"""
    #instanciate a venue data list to contain all data for a specific venue in a specific location
    single_venue_data = []
    #loop over venues 
    for venue in venues :
      #aggregate data by location
      if (location[0] == venue.city) and (location[1] == venue.state):
        shows_per_venue_in_location = Show.query.filter_by(venue_id=venue.id).all()
        num_upcoming = 0 
        for show in shows_per_venue_in_location : 
          if show.start_time > current_time :
            num_upcoming += 1
        
        single_venue_data.append({
          "id" : venue.id,
          "name" : venue.name,
          "num_upcoming" : num_upcoming
          })

    data.append({
      "city" : location[0],
      "state" : location[1],
      "venues" : single_venue_data
    })
  
  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():

  search_term = request.form.get('search_term', '')
  search_result = db.session.query(Venue).filter(Venue.name.ilike(f'%{search_term}%')).all()
  data=[]
  for result in search_result:
    current_time = datetime.now()
    data.append({
      'id': result.id,
      'name': result.name,
      'num_upcoming_shows': len(db.session.query(Show).filter(Show.venue_id == result.id).filter(Show.start_time > current_time ).all())
    })
  response={
    "count": len(search_result),
    "data": data
    }
  
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

  venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
  if not venue:
    return redirect(url_for('index'))

  else :
    current_time = datetime.now()
    past_shows_results= db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id).filter(Show.start_time <= current_time ).all()
    past_shows = []
    for show in past_shows_results :
      past_shows.append({
        "artist_id" : show.artist.id,
        "artist_name" : show.artist.name,
        "artist_image_link" : show.artist.image_link,
        #TypeError: Parser must be a string or character stream, not datetime
        "start_time" : show.start_time.strftime('%Y-%m-%d %H:%M:%S')
      })

    upcoming_shows_results= db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id).filter(Show.start_time > current_time ).all()
    upcoming_shows = []
    for show in upcoming_shows_results :
      upcoming_shows.append({
        "artist_id" : show.artist.id,
        "artist_name" : show.artist.name,
        "artist_image_link" : show.artist.image_link,
        #TypeError: Parser must be a string or character stream, not datetime
        "start_time" : show.start_time.strftime('%Y-%m-%d %H:%M:%S')
    })
 
    data = {
      "id" : venue.id,
      "name": venue.name,
      "genres": venue.genres,
      "address": venue.address,
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "website": venue.website_link,
      "facebook_link": venue.facebook_link,
      "seeking_talent": venue.seeking_talent,
      "seeking_description": venue.seeking_description,
      "image_link": venue.image_link,
      "past_shows": past_shows,
      "upcoming_shows" : upcoming_shows,
      "past_shows_count" : len(past_shows),
      "upcoming_shows_count" : len(upcoming_shows)}

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  form = VenueForm(request.form)
  try :
    new_venue=Venue(name = form.name.data,
    city = form.city.data,
    state = form.state.data,
    address = form.address.data,
    phone = form.phone.data,
    genres = form.genres.data,
    image_link = form.image_link.data,
    facebook_link = form.facebook_link.data,
    website_link = form.website_link.data,
    seeking_talent = True if "seeking_talent" in request.form else False,
    seeking_description = form.seeking_description.data)
    
    db.session.add(new_venue)
    db.session.commit()
    # on successful db insert, flash success
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except ValueError as e :
    db.session.rollback()
    # on unsuccessful db insert, flash an error instead.
    flash('An error occurred. Venue ' + request.form['name']  + ' could not be listed.')
  finally :
    db.session.close()
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
  try :
    db.session.delete(venue)
    db.session.commit()
    flash(f'Venue {venue.name} was successfully deleted.')
  except:
    db.session.rollback()
    flash(f'An error occurred. Venue {venue.name} could not be deleted.')
  finally:
    db.session.close()
      
  return redirect(url_for('index'))

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.all()

  data = []
  for artist in artists:
    data.append({
          "id" : artist.id,
          "name" : artist.name })
  
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  search_result = db.session.query(Artist).filter(Artist.name.ilike(f'%{search_term}%')).all()
  data=[]
  for result in search_result:
    current_time = datetime.now()
    data.append({
      'id': result.id,
      'name': result.name,
      'num_upcoming_shows': len(db.session.query(Show).filter(Show.artist_id == result.id).filter(Show.start_time > current_time ).all())
    })
  response={
    "count": len(search_result),
    "data": data
    }

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

  artist = db.session.query(Artist).filter(Artist.id == artist_id).first()
  if not artist:
    return redirect(url_for('index'))

  else :
    current_time = datetime.now()
    past_shows_results= db.session.query(Show).join(Venue).filter(Show.artist_id == artist_id).filter(Show.start_time <= current_time ).all()
    past_shows = []
    for show in past_shows_results :
      past_shows.append({
        "venue_id" : show.venue.id,
        "venue_name" : show.venue.name,
        "venue_image_link" : show.venue.image_link,
        #TypeError: Parser must be a string or character stream, not datetime
        "start_time" : show.start_time.strftime('%Y-%m-%d %H:%M:%S')
      })

    upcoming_shows_results= db.session.query(Show).join(Venue).filter(Show.artist_id == artist_id).filter(Show.start_time > current_time ).all()
    upcoming_shows = []
    for show in upcoming_shows_results :
      upcoming_shows.append({
        "venue_id" : show.venue.id,
        "venue_name" : show.venue.name,
        "venue_image_link" : show.venue.image_link,
        #TypeError: Parser must be a string or character stream, not datetime
        "start_time" : show.start_time.strftime('%Y-%m-%d %H:%M:%S')
    })

    data = {
      "id" : artist.id,
      "name": artist.name,
      "genres": artist.genres,
      "city": artist.city,
      "state": artist.state,
      "phone": artist.phone,
      "website": artist.website_link,
      "facebook_link": artist.facebook_link,
      "seeking_venue": artist.seeking_venue,
      "seeking_description": artist.seeking_description,
      "image_link": artist.image_link,
      "past_shows": past_shows,
      "upcoming_shows" : upcoming_shows,
      "past_shows_count" : len(past_shows),
      "upcoming_shows_count" : len(upcoming_shows)}

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = db.session.query(Artist).filter(Artist.id == artist_id).first()
  if artist :
    form.name.data = artist.name
    form.city.data = artist.city
    form.state.data = artist.state
    form.phone.data = artist.phone
    form.genres.data = artist.genres
    form.facebook_link.data = artist.facebook_link
    form.image_link.data = artist.image_link
    form.website_link.data = artist.website_link
    form.seeking_venue.data = artist.seeking_venue
    form.seeking_description.data = artist.seeking_description

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):

  artist = db.session.query(Artist).filter(Artist.id == artist_id).first()
  form = ArtistForm(request.form)
  try : 
    artist.name = request.form["name"]
    artist.city = form.city.data,
    artist.state = form.state.data,
    artist.phone = form.phone.data,
    artist.genres = form.genres.data,
    artist.image_link = form.image_link.data,
    artist.facebook_link = form.facebook_link.data,
    artist.website_link = form.website_link.data,
    artist.seeking_venue = True if 'seeking_venue' in request.form else False 
    artist.seeking_description = form.seeking_description.data
  

    db.session.commit()
    flash(f'Artist was successfully updated!')
  except :
    db.session.rollback()
    flash(f'An error occurred. Artist could not be changed.')
  finally :
    db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
  if venue : 
    form.name.data = venue.name
    form.city.data = venue.city
    form.state.data = venue.state
    form.phone.data = venue.phone
    form.address.data = venue.address
    form.genres.data = venue.genres
    form.facebook_link.data = venue.facebook_link
    form.image_link.data = venue.image_link
    form.website_link.data = venue.website_link
    form.seeking_talent.data = venue.seeking_talent
    form.seeking_description.data = venue.seeking_description

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

  venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
  form = VenueForm(request.form)
  try : 
    venue.name = form.name.data
    venue.city = form.city.data
    venue.state = form.state.data
    venue.address = form.address.data
    venue.phone = form.phone.data
    venue.genres = form.genres.data
    venue.image_link = form.image_link.data
    venue.facebook_link = form.facebook_link.data
    venue.website_link = form.website_link.data
    venue.seeking_talent = True if 'seeking_talent' in request.form else False 
    venue.seeking_description = form.seeking_description.data

    db.session.commit()
    flash(f'Venue was successfully updated!')
  except :
    db.session.rollback()
    flash(f'An error occurred. Venue could not be changed.')
  finally :
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  form = ArtistForm(request.form)
  try :
    new_artist=Artist(name=request.form["name"], 
      city=form.city.data,
      state = form.state.data,
      phone = form.phone.data,
      genres = form.genres.data,
      image_link = form.image_link.data,
      facebook_link = form.facebook_link.data,
      website_link = form.website_link.data,
      seeking_venue = True if "seeking_venue" in request.form else False,
      seeking_description = form.seeking_description.data
    )
    db.session.add(new_artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except ValueError as e : 
    print (e)
    db.session.rollback()
    flash('Artist ' + request.form['name'] + ' was successfully listed')



  finally : 
    db.session.close()

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = []
  shows = db.session.query(Show).join(Venue).join(Artist).all()
  for show in shows : 
    data.append({
      "venue_id" : show.venue_id,
      "venue_name": show.venue.name,
      "artist_id": show.artist_id,
      "artist_name": show.artist.name,
      "artist_image_link": show.artist.image_link,
      #TypeError: Parser must be a string or character stream, not datetime
      "start_time" : show.start_time.strftime('%Y-%m-%d %H:%M:%S')
       })

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try : 
    new_show = Show(venue_id = request.form["venue_id"],
    artist_id = request.form["artist_id"],
    start_time = request.form["start_time"])

    db.session.add(new_show)
    db.session.commit()
    flash('Show was successfully listed!')

  except ValueError as e: 
    print(e)
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
  finally : 
    db.session.close()

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
