# -*- coding: utf8 -*-

import phpserialize
import MySQLdb
import urllib2
import itertools
import settings


class StalkerDB:
	def __init__(self, host, user, passwd, db):
		db = MySQLdb.connect(host=host, user=user, passwd=passwd, db=db)
		self.__cursor = db.cursor()
		self.__cursor.execute('SET NAMES UTF8;')

	def query(self, sql):
		self.__cursor.execute(sql)
		return self.__cursor

class Saver:
    def save(self):
	with open('%s/%s.m3u' % (self.get_root().settings.BASE_DIR, self.filename()), 'wt') as f:
	    f.write(self.content())

    def print_all(self):
	return ""

    def content(self):
	s = "#EXTM3U\n"
	s += self.print_all()
	for x in self.childs():
	    s += x.get_m3u()
	return s

    def get_m3u(self):
	return "#EXTINF:0 tvg-logo=\"%s\", %s\n%s\n" % (self.logo(), self.name(), self.url())

    def url(self):
	return '%s/%s.m3u' % (self.get_root().settings.BASE_URL, self.filename())

    def logo(self):
	return self.get_root().settings.STALKER_URL + '/nofilm.png'


class Root(Saver):
    def __init__(self, st, settings):
	self.st = st
	self.settings = settings

    def get_root(self):
	return self

    def filename(self):
	return 'films'

    def get_categories(self):
	sql = "SELECT DISTINCT category_alias FROM cat_genre;"
	for category_alias in self.st.query(sql):
	    yield Category(self, category_alias[0])

    childs = get_categories


class File:
    def __init__(self, film, fn):
	self.film = film
	self.fn = fn

    def get_root(self):
	return self.film.get_root()

    def url(self):
	ip = self.film.storage_ip
	if ip in self.get_root().settings.IPS.keys():
	    ip = self.get_root().settings.IPS[ip]
	return 'http://%s/storage/%s/%s' % (ip, self.film.path, urllib2.quote(self.fn))

    def get_m3u(self):
	ser = '%s серия' % self.fn.split('.')[-2]
	return "#EXTINF:0, %s %s\n%s\n" % (self.film.name(), ser, self.url())


class Film(Saver):
    def __init__(self, category, film_id, storage_data, path, storage_ip, name, o_name, year):
	self.film_id = film_id
	self.category = category
	self.data = phpserialize.loads(storage_data)
	self.path = path
	self.storage_ip = storage_ip
	self.l_name = name
	self.o_name = o_name
	self.year = year

    def __hash__(self):
	return self.film_id

    def __eq__(x, y):
        return hash(x) == hash(y)

    def get_root(self):
	return self.category.get_root()

    def filename(self):
	return self.film_id

    def name(self):
	return '%s %s (%s)' % (self.l_name, self.year, self.o_name)

    def is_serial(self):
	return len(self.data['files'].items()) != 1

    def get_files(self):
	return [File(self, x['name']) for x in sorted(self.data['files'].values())]

    childs = get_files

    def url(self):
	if self.is_serial():
	    return '%s/%s.m3u' % (self.get_root().settings.BASE_URL, self.filename())
	else:
	    return self.get_files()[0].url()

    def logo(self):
	cat = self.film_id / 100
	if self.film_id % 100 != 0:
	    cat += 1
	return '%s/screenshot/%d/%d.jpg' % (self.get_root().settings.STALKER_URL, cat, self.film_id)



class Genre(Saver):
    __LOCAL = {
	'our cartoons': 'Отечественные мультфильмы',
	'teach': 'Образовательные',
	'foreign cartoons': 'Иностранные мультфильмы',
	'cartoon series': 'Мультсериалы',
	'biography': 'Биография',
	'military': 'Военное',
	'history': 'Историческое',
	'art': 'Искусство',
	'criminal': 'Криминал',
	'catastrophe': 'Катастрофы',
	'travels': 'Путешествия',
	'mysticism': 'Мистика',
	'technique': 'Техника',
	'science': 'Наука',
	'fiction': 'Фантастика',
	'nature': 'Природа',
	'health': 'Здоровье',
	'erotica': 'Эротика',
	'show': 'Шоу',
	'sketch-show': 'Скетчшоу',
	'humourist': 'Юмор',
	'sport': 'Спорт',
	'hunting': 'Охота',
	'dancing': 'Танцы',
	'cookery': 'Готовка',
	'house/country': 'Дом, дача',
	'fishing': 'Рыбалка',
	'aerobics': 'Аэробика',
	'yoga': 'Йога',
	'action': 'Боевик',
	'drama': 'Драма',
	'detective': 'Детективы',
	'historical': 'Историческое',
	'comedy': 'Комедии',
	'melodrama': 'Мелодраммы',
	'musical': 'Музыкальное',
	'adventure': 'Приключения',
	'thriller': 'Триллеры',
	'fantasy': 'Фэнтези',
	'horror': 'Ужасы',
	'children\'s': 'Детское',
	'western': 'Вестерн',
    }

    def __init__(self, category, genre_id, name):
	self.category = category
	self.genre_id = genre_id
	self.genre_name = name

    def get_root(self):
	return self.category.get_root()

    def name(self):
	if self.genre_name in self.__LOCAL.keys():
	    return self.__LOCAL[self.genre_name]
	return self.genre_name

    def filename(self):
	return '%s-%s'% (self.category.filename(), self.genre_name.replace('/', ',').replace(' ', '_'))

    def get_films(self):
	sql = """
	    SELECT video.id, storage_data, path, storage_ip, name, o_name, year
	    FROM storage_cache
	    INNER JOIN video ON storage_cache.media_id = video.id
	    INNER JOIN storages ON storage_cache.storage_name = storages.storage_name
	    WHERE cat_genre_id_1 = {0}
	    OR cat_genre_id_2 = {0} OR cat_genre_id_3 = {0}
	    OR cat_genre_id_4 = {0}
	    ORDER BY name
	""".format(self.genre_id)
	for film_id, storage_data, path, storage_ip, name, o_name, year in self.get_root().st.query(sql):
	    yield Film(self, film_id, storage_data, path, storage_ip, name, o_name, year)

    childs = get_films


class CategoryAll(Saver):
    def __init__(self, category):
	self.category = category

    def get_root(self):
	return self.category.root

    def name(self):
	return 'Все'

    def filename(self):
	return '%s-%s' % (self.category.filename(), 'all')

    def get_films(self):
	return self.category.get_films()

    childs = get_films


class Category(Saver):
    __LOCAL = {
	'animation': 'Мультфильмы',
	'doc_film': 'Докуметральные',
	'humor': 'Юмор',
	'liking': 'Увлечения',
	'our_film': 'Отечественные фильмы',
	'owr_serial': 'Отечественные сериалы',
	'world_film': 'Зарубежные фильмы',
	'world_serial': 'Зарубежные сериалы',
    }
    def __init__(self, root, name):
	self.root = root
	self.category_name = name

    def get_root(self):
	return self.root

    def filename(self):
	return self.category_name

    def name(self):
	if self.category_name in self.__LOCAL.keys():
	    return self.__LOCAL[self.category_name]
	return self.category_name

    def get_films(self):
	films = set()
	for g in self.get_genres_single():
	    for f in g.get_films():
		films.add(f)
	return sorted(list(films), key=lambda x: x.name())

    def get_genres_single(self):
	sql = "SELECT id, title FROM cat_genre WHERE category_alias = '%s';" % self.category_name
	for genre_id, genre_title in self.root.st.query(sql):
	    yield Genre(self, genre_id, genre_title)

    def category_all_generator(self):
	yield CategoryAll(self)

    def get_genres(self):
	return itertools.chain(self.category_all_generator(), self.get_genres_single())

    childs = get_genres


st = StalkerDB(settings.DB_HOST, settings.DB_USER, settings.DB_PASS, settings.DB_DATABASE)

root = Root(st, settings)


root.save()
for category in root.get_categories():
    print '#', category.name()
    category.save()
#    CategoryAll(category).save()
    for genre in category.get_genres():
	print '##', genre.name()
	genre.save()
	for film in genre.get_films():
	    if film.is_serial():
		film.save()
#    print list(category.get_genres())

