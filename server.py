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
    for tag in root.xpath('//style'):
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
    criteria = [wq.Term('user', user)]
    if query is not None and query.strip() != '':
        Terms = [wq.Term('content', term) for term in query.strip().split()]
        criteria.append(wq.Or(Terms))
    query = wq.And(criteria)
    return query 


@api.route('/links')
def accept_url():
    store_page(request.args['user'], request.args['url'])
    return 'done'


@api.route('/search')
def search():
    results = []
    with idx.searcher() as searcher:
        query = make_query(request.args['user'], request.args.get('query'))
        results = map(parse_result, searcher.search(query, limit=10000))
    method_name = request.args.get('sortby', 'score')
    sort_keys = {
            'date': lambda r: r['date'],
            'score': lambda r: r['score']
            }
    results.sort(key=sort_keys[method_name], reverse=True)
    return render_template('index.html',
            results=results,
            byscore=(method_name=='score'),
            query=request.args.get('query'))


def parse_result(result): 
    return {
        'highlight': result.highlights('content'),
        'date': result['ts'],
        'url': result['url'],
        'score': result.score
        }


if __name__ == '__main__':
    api.run(debug=True)
