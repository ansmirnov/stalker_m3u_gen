# -*- coding: utf8 -*-

import phpserialize
import _mysql
import urllib2

db = _mysql.connect(host=settings.DB_HOST, user=settings.DB_USER, passwd=settings.DB_PASS, db=settings.DB_DATABASE)

db.query('SET NAMES UTF8;')

sql = "SELECT storage_data, path, storage_ip, name, o_name, title, year FROM storage_cache INNER JOIN video ON storage_cache.media_id = video.id INNER JOIN storages ON storage_cache.storage_name = storages.storage_name INNER JOIN cat_genre ON cat_genre_id_1 = cat_genre.id ORDER BY name"

db.query(sql)

r = db.store_result()

print '#EXTM3U m3uautoload=1 cache=2000'

for x in r.fetch_row(how=1, maxrows=0):
    try:
	data, path, ip, name, group_title, year = phpserialize.loads(x['storage_data']), x['path'], x['storage_ip'], '%s %s (%s)' % (x['name'], x['year'], x['o_name']), x['title'], x['year']
    except:
	continue
    i = 0
    for x in sorted(data['files'].values()):
	i += 1
        fn = x['name']
	if len(data['files'].items()) != 1:
	    continue
    #    fn = data['first_media']
	url = 'http://%s/storage/%s/%s' % (ip, path, urllib2.quote(fn))
	if len(data['files'].items()) != 1:
	    ser = ' %s серия' % fn.split('.')[-2]
	else:
	    ser = ''
        print '#EXTINF:-1 deinterlace=1 group-title="%s",%s%s' % (group_title, name, ser)
	print url
