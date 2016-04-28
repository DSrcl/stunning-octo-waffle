from whoosh.index import create_in, open_dir
from whoosh import fields
from whoosh import query as wq
from whoosh.writing import AsyncWriter
import requests
import os
from flask import Flask, request, render_template
from datetime import datetime
from lxml import etree

api = Flask(__name__)

# TODO
# * fix locking bug
# * make `accept_url` async
# * make the page look a bit nicer

schema = fields.Schema(ts=fields.DATETIME(stored=True),
        user=fields.ID(stored=True),
        url=fields.ID(stored=True),
        content=fields.TEXT(stored=True))

indexdir = "indexdir"

if not os.path.isdir(indexdir):
    os.mkdir(indexdir)
    idx = create_in(indexdir, schema)
else:
    idx = open_dir(indexdir)


def parse(page):
    root = etree.HTML(page)
    # filter out javascript code
    for tag in root.xpath('//script'):
        tag.getparent().remove(tag)
    return unicode(''.join(root.itertext()))


# download url and index it
# TODO make this async
def store_page(user, url):
    writer = AsyncWriter(idx)
    resp = requests.get(url)
    content = parse(resp.content)
    now = datetime.now()
    writer.add_document(ts=now, user=unicode(user), url=unicode(url), content=content)
    writer.commit()


def make_query(user, query):
    query = wq.And([wq.Term('content', query), wq.Term('user', user)])
    return query


@api.route('/links')
def accept_url():
    store_page(request.args['user'], request.args['url'])
    return 'done'


@api.route('/search')
def search():
    results = []
    if 'user' in request.args and 'query' in request.args:
        with idx.searcher() as searcher:
            query = make_query(request.args['user'], request.args['query'])
            results = map(parse_result, searcher.search(query))
    return render_template('index.html', results=results)
    


def parse_result(result): 
    return {
        'highlight': result.highlights('content'),
        'date': result['ts'],
        'url': result['url']
        }


if __name__ == '__main__':
    api.run(debug=True)
