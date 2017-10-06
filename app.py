import os
import requests
import operator
import re
import nltk
from flask import Flask, render_template, request
# from flask.ext.sqlalchemy import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from stop_words import stops
from collections import Counter
from bs4 import BeautifulSoup
from rq import Queue
from rq.job import Job
from worker import conn
from flask import jsonify
import json
from kmeans_clustering import cluster_docs


os.environ["DATABASE_URL"] = "postgresql:///wordcount_dev"
os.environ["APP_SETTINGS"] = "config.DevelopmentConfig"
app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

q = Queue(connection=conn)

from models import Result


def update_db_result(cluster_number_start, cluster_number_end, silhouette_scores, word_lists):
    errors = []

    try:
        result = Result(
            url='',
            result_all=[],
            result_no_stop_words=[],
            cluster_number_start=cluster_number_start,
            cluster_number_end=cluster_number_end,
            silhouette_scores=silhouette_scores,
            word_lists=word_lists
        )
        db.session.add(result)
        db.session.commit()
        print('result.id: ' + str(result.id))
        return result.id
    except Exception as e:
        errors.append("Unable to add item to database.")
        print('error: Unable to add item to database.')
        print(e.message)
        return {"error": e.message}
    pass


def analysis_kmeans_cluster_number(**kwargs):
    path = kwargs.get('path')
    mode = kwargs.get('mode')
    range_s = kwargs.get('range_start')
    range_e = kwargs.get('range_end')

    print('set path: ' + path)
    print('set mode: ' + mode)
    print('set range start: ' + range_s)
    print('set range end: ' + range_e)

    ret = cluster_docs(mode, range_s, range_e)

    silhouette_scores = []
    word_lists = []
    if mode == 'silhouette_analysis':
        silhouette_scores = [str(i) for i in ret]
        print('silhouette_scores:')
        print(silhouette_scores)
        print('json format: ')
        print(json.dumps(silhouette_scores))
    elif mode == 'elbow_analysis':
        pass
    elif mode == 'cluster':
        word_lists = ret
        print('word_lists:')
        print(word_lists)
        print('json format: ')
        print(json.dumps(word_lists))

    return update_db_result(cluster_number_start=int(range_s), cluster_number_end=int(range_e), silhouette_scores=json.dumps(silhouette_scores), word_lists=word_lists)
    pass


def execute_kmeans_clustering():
    pass


def count_and_save_words(url):

    errors = []

    try:
        r = requests.get(url)
    except:
        errors.append(
            "Unable to get URL. Please make sure it's valid and try again."
        )
        return {"error": errors}

    # text processing
    raw = BeautifulSoup(r.text, 'html.parser').get_text()
    nltk.data.path.append('./nltk_data/')  # set the path
    tokens = nltk.word_tokenize(raw)
    text = nltk.Text(tokens)

    # remove punctuation, count raw words
    nonPunct = re.compile('.*[A-Za-z].*')
    raw_words = [w for w in text if nonPunct.match(w)]
    raw_word_count = Counter(raw_words)

    # stop words
    no_stop_words = [w for w in raw_words if w.lower() not in stops]
    no_stop_words_count = Counter(no_stop_words)

    # save the results
    results = sorted(
        no_stop_words_count.items(),
        key=operator.itemgetter(1),
        reverse=True
    )
    try:
        result = Result(
            url=url,
            result_all=raw_word_count,
            result_no_stop_words=no_stop_words_count
        )
        db.session.add(result)
        db.session.commit()
        return result.id
    except Exception as e:
        errors.append("Unable to add item to database.")
        return {"error": e.message}


@app.route('/', methods=['GET', 'POST'])
def index():
    # errors = []
    # results = {}
    # if request.method == "POST":
    #     # get url that the person has entered
    #     url = request.form['url']
    #     # if 'http://' not in url[:7]:
    #     #     url = 'http://' + url
    #     job = q.enqueue_call(
    #         func=count_and_save_words, args=(url,), result_ttl=5000
    #     )
    #     print(job.get_id())
    #
    # return render_template('index.html', results=results)
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def get_counts():
    # get url
    data = json.loads(request.data.decode())
    url = data["url"]
    path = data["path"]
    range_s = data["range_start"]
    range_e = data["range_end"]
    mode = data["mode"]

    print('path: ' + path)
    print('range_start: ' + range_s)
    print('range_end: ' + range_e)
    print('mode: ' + mode)

    if 'http://' not in url[:7]:
        url = 'http://' + url
    # start job
    job = q.enqueue_call(
        # func=count_and_save_words, args=(url,), result_ttl=5000
        func=analysis_kmeans_cluster_number, kwargs={'path': path, 'mode': mode, 'range_start': range_s, 'range_end': range_e}, result_ttl=5000, timeout=60 * 60
    )
    # return created job id
    print('jobID: ' + str(job.get_id))
    return job.get_id()


@app.route("/results/<job_key>", methods=['GET'])
def get_results(job_key):

    job = Job.fetch(job_key, connection=conn)

    if job.is_finished:
        # return "OK", 200
        print('result id: ' + str(job.result))
        result = Result.query.filter_by(id=job.result).first()
        # results = sorted(
        #     result.result_no_stop_words.items(),
        #     key=operator.itemgetter(1),
        #     reverse=True
        # )[:10]
        silhouette_scores = result.silhouette_scores
        print('silhouette_scores type: ')
        print(type(silhouette_scores))
        print('silhouette_scores: ')
        print(silhouette_scores)

        # TODO: should use a better judge method
        if silhouette_scores != '[]':
            # silhouette_analysis mode
            silhouette_scores = re.sub('[\[\]\"]', '', silhouette_scores)
            print('new silhouette_scores: ')
            print(silhouette_scores)

            scores = silhouette_scores.split(',')
            print('scores: ')
            print(scores)

            print('from ' + str(result.cluster_number_start) + ' to ' + str(result.cluster_number_end))
            clusters = list(range(int(result.cluster_number_start), int(result.cluster_number_end) + 1))
            print('cluster: ')
            print(clusters)

            cluster_scores = dict(zip(clusters, scores))
            print('cluster_scores:')
            print(cluster_scores)

            return jsonify(cluster_scores), 200
        else:
            print('from ' + str(result.cluster_number_start) + ' to ' + str(result.cluster_number_end))

            # TODO: should use a better judge method
            if int(result.cluster_number_start) < int(result.cluster_number_end):
                # elbow_analysis mode
                cluster_range = str(result.cluster_number_start) + '~' + str(result.cluster_number_end)
                print('cluster_range: ' + cluster_range)
                return cluster_range, 201
            elif int(result.cluster_number_start) == int(result.cluster_number_start):
                # cluster mode
                word_lists = result.word_lists
                print('word_lists type: ')
                print(type(word_lists))
                print('word_lists: ')
                print(word_lists)

                group_num = list(range(1, int(result.cluster_number_start) + 1))
                print('group_num: ')
                print(group_num)

                cluster_results = dict(zip(group_num, word_lists))
                print('cluster_results:')
                print(cluster_results)
                return jsonify(cluster_results), 203
    else:
        return "Nay!", 202


if __name__ == '__main__':
    app.run()