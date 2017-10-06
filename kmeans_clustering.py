# -*- coding: utf-8 -*-
import os
from os.path import join, dirname
import MeCab
import gensim
import codecs
import numpy as np
from sklearn.cluster import KMeans
from os.path import basename
from progressbar import ProgressBar
import pickle
import requests
from collections import defaultdict
import word_cloud
from datetime import datetime
import json
from kmeans_cluster_numbers import silhouette_analysis
import matplotlib.pyplot as plt
import commands


HOME = os.path.expanduser("~")
DATASET_PATH_1 = u'青空文庫2'
DATASET_PATH_2 = u'trialdata'
FESS_FILE_SERVER = '10.155.37.21:8081'
LOCAL_MODE = 'local'
REMOTE_MODE = 'remote'
NUM_TOPICS = 1
TOPN = 30
num_topics = 10


PICKLE_DOC = 'dataset_doc.npy'
PICKLE_NAME = 'dataset_name.npy'
PICKLE_PATH = 'dataset_path.npy'

def unpickle(filename):
    with open(filename, 'rb') as fo:
        p = pickle.load(fo)
    return p


def to_pickle(filename, obj):
    with open(filename, 'wb') as f:
        pickle.dump(obj, f, -1)
    pass


def query_fessfile(query_words, db=None):
    des = 'http://' + FESS_FILE_SERVER
    content_list = []
    # query_words =[u'GUI', u'VxWorks', u'Windows', u'医療', u'OS', u'通信', u'UI', u'リスク', u'課題', u'施策']
    # query_words = [u'憲章']

    # f = codecs.open(FILECONTENT_PATH, 'a', 'utf8')

    for query_word in query_words:
        file_idx = -1

        first_time = True
        old_query_word = None
        while True:
            base_url = des + '/fessfile/json?q=title:' + query_word
            if '(' in base_url:
                base_url = base_url.replace('(', '\(')
            if ')' in base_url:
                base_url = base_url.replace(')', '\)')

            if first_time:
                first_time = False
                query_url = base_url
                pass

            response = requests.get(query_url)

            resp = response.json()['response']
            if 'result' in resp:
                resp_ret = resp['result']
                page_count = resp['page_count']
                page_number = resp['page_number']
                page_size = resp['page_size']
                record_count = resp['record_count']
            else:
                print('file name: ' + query_word)
                print('digest   : NONE')
                if old_query_word == query_word:
                    break
                else:
                    old_query_word = query_word
                    continue

            digest = [ret['digest'] for ret in resp_ret]
            # digest_list.append(digest)
            # print('file name: ' + query_word.encode('utf-8'))
            # print('digest   : ' + digest[0].encode('utf-8'))
            fileContent = [ret['content'] for ret in resp_ret
                           if ret['content'] != '']
            if len(fileContent) > 0:
                content_list.append(fileContent)
                # for line in fileContent:
                #    f.write(line + '\n')
                file_idx = len(content_list) - 1

            if page_number * page_size >= record_count:
                break
            else:
                increasement = page_number * page_size
                query_url = base_url + '&start=' + str(increasement)
                pass
            pass

        if db is not None:
            db.execute(u"""INSERT INTO projectfilelist(FILE_NAME,FILE_LIST_IDX)
                    VALUES (?, ?)""", (query_word, file_idx,))
            db.commit()

    # f.close()
    return content_list


def get_filepaths(directory):
    """
    This function will generate the file names in a directory
    tree by walking the tree either top-down or bottom-up. For each
    directory in the tree rooted at directory top (including top itself),
    it yields a 3-tuple (dirpath, dirnames, filenames).
    """
    file_paths = []  # List which will store all of the full filepaths.

    # Walk the tree.
    for root, directories, files in os.walk(directory):
        for filename in files:
            # Join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)  # Add it to the list.

    return file_paths  # Self-explanatory.


def parse_mecab(text, word_list):
    # reference to list supporting append method

    m = MeCab.Tagger(' -d /var/lib/mecab/dic/debian')
    for sentence in text:
        r = m.parseToNode(sentence.encode('utf-8'))
        while r:
            attribute = r.feature.split(",")
            mecabed_word = attribute[6]
            word_list.append(mecabed_word)
            r = r.next
    pass


def get_docs(data_set_path, data_set_mode=LOCAL_MODE):
    docs = {}
    file_names = []
    file_paths = []
    full_file_paths = get_filepaths(data_set_path)

    pb = ProgressBar(maxval=len(full_file_paths)).start()
    for i, file_path in enumerate(full_file_paths):
        pb.update(i)

        docname = basename(file_path)
        if docname in file_names:
            print(docname + ' is duplicated!')
            continue

        if data_set_mode == LOCAL_MODE:
            try:
                f = codecs.open(file_path, 'r', 'shift_jis')
                lines = f.readlines()
                docs[docname] = []
                file_names.append(docname)
                file_paths.append(file_path)
                parse_mecab(lines, docs[docname])
                f.close()
            except Exception as e:
                if type(e) is UnicodeDecodeError:
                    print('An UnicodeDecodeError! ' + docname)
                    continue

        elif data_set_mode == REMOTE_MODE:
            fess_contents_list = query_fessfile(query_words=[docname])
            if len(fess_contents_list) == 0:
                print('\n' + docname + ' can not get contents!')
                continue

            docs[docname] = []
            file_names.append(docname)
            file_paths.append(file_path)
            for fileContent in fess_contents_list:
                parse_mecab(fileContent, docs[docname])
            pass

    return docs, file_names, file_paths


def vec2dense(vec, num_terms):
    return list(gensim.matutils.corpus2dense([vec], num_terms=num_terms).T[0])


def list_duplicates(seq):
    tally = defaultdict(list)
    for i, item in enumerate(seq):
        tally[item].append(i)
    return ((key, locs) for key, locs in tally.items()
            if len(locs) > 1)


def get_content(file_path, mode=LOCAL_MODE):
    content = ''
    if mode == LOCAL_MODE:
        try:
            f = codecs.open(file_path, 'r', 'shift_jis')
            content = f.readlines()
            f.close()
        except Exception as e:
            if type(e) is UnicodeDecodeError:
                print('An UnicodeDecodeError! ' + file_path)

    elif mode == REMOTE_MODE:
        file_name = os.path.splitext(basename(file_path))[0]
        fess_contents_list = query_fessfile(query_words=[file_name])
        if len(fess_contents_list) == 0:
            print('\n' + file_name + ' can not get contents!')
        else:
            for fileContent in fess_contents_list:
                content += fileContent

    return content


def prepare_termextract():
    mode = 'store'
    dataset = join(HOME, DATASET_PATH_1)
    termCommand = 'python3 termextract_toolkit.py' + ' -m ' + mode + ' -d ' + dataset
    # resp = commands.getoutput('%s' % (termCommand))
    # print('resp:---' + resp + '---')
    pass


def get_terms(method, files):
    termCommand = 'python3 termextract_toolkit.py -m multi-analysis ' + ' -t ' + method + ' -f ' + "\"" + files + "\""
    resp = commands.getoutput('%s' % (termCommand))
    # print('resp:---' + resp + '---')
    terms = resp.split('\n')
    return terms[0:TOPN]


def get_topics(corpus, dictionary):
    topics = []

    print('create LDA model ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    ldamodel = gensim.models.LdaModel(corpus, num_topics=NUM_TOPICS, id2word=dictionary, passes=20)
    for i in range(NUM_TOPICS):
        top_topics = ldamodel.print_topic(i, topn=TOPN).encode('utf-8').split('+')
        for top_topic in top_topics:
            topic_word = top_topic.split('*')[1].replace('\"', '')
            topics.append(topic_word)
        pass

    return topics


def cluster_docs(mode='cluster', range_s=1, range_e=1):
    print('# MORPHOLOGICAL ANALYSIS ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    # docs, file_names, file_paths = get_docs(join(HOME, DATASET_PATH_1), LOCAL_MODE)
    prepare_termextract()

    # print('save doc to file')
    # to_pickle(PICKLE_DOC, docs)
    # to_pickle(PICKLE_NAME, file_names)
    # to_pickle(PICKLE_PATH, file_paths)
    print('get doc from saved file ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    docs = unpickle(PICKLE_DOC)
    file_names = unpickle(PICKLE_NAME)
    file_paths = unpickle(PICKLE_PATH)

    print('create dictionary ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    dct = gensim.corpora.Dictionary(docs.values())
    print('extreme filter ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    dct.filter_extremes(no_below=2, no_above=0.1)
    filtered = dct.token2id.keys()
    print 'number of features', len(filtered)
    #  for key in filtered:
    #    print key

    print("# BAG OF WORDS " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    bow_docs = {}
    for docname in file_names:
        bow_docs[docname] = dct.doc2bow(docs[docname])

    print('# LSI Model ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    dimension = num_topics + 3
    lsi_model = gensim.models.LsiModel(bow_docs.values(), num_topics=dimension)
    lsi_docs = {}
    for i, docname in enumerate(file_names):
        vec = bow_docs[docname]
        lsi_docs[i] = lsi_model[vec]

    print('# Clustering ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    data_all = [vec2dense(lsi_docs[i], dimension) for i, docname in enumerate(file_names)]
    normalized = [vec / np.linalg.norm(vec) for vec in data_all]
    cleanedList = []
    filtered_file_name = []
    for j, x in enumerate(normalized):
        if np.isnan(x).any() != True:
            cleanedList.append(x)
            filtered_file_name.append(file_paths[j])
        else:
            print(file_names[j] + ' can not be normalized!')
        pass

    # find optimal cluster numbers
    if mode == 'elbow_analysis':
        distortions = []
        for i in range(int(range_s), int(range_e)):  # 1~10クラスタまで一気に計算
            km = KMeans(n_clusters=i,
                        init='k-means++',  # k-means++法によりクラスタ中心を選択
                        n_init=10,
                        max_iter=300,
                        random_state=0)
            km.fit(cleanedList)  # クラスタリングの計算を実行
            distortions.append(km.inertia_)  # km.fitするとkm.inertia_が得られる

        plt.plot(range(int(range_s), int(range_e)), distortions, marker='o')
        plt.xlabel('Number of clusters')
        plt.ylabel('Distortion')
        # plt.show()
        plt.savefig('static/elbow_analysis_'+ range_s + '~' + range_e +  '.png')
        return

    if mode == 'silhouette_analysis':
        # range_n_clusters = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        range_n_clusters = list(range(int(range_s), int(range_e)+1))
        return silhouette_analysis(cleanedList, range_n_clusters)

    result = KMeans(n_clusters=num_topics).fit_predict(cleanedList)
    for i, docname in enumerate(filtered_file_name):
        print docname, 'cluster', result[i]

    print('# Show topics ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    # find same items in result and collect them from docname
    # then get LDA topics for this collected content
    cluster_result_doc = {}
    cluster_result_word = {}
    for dup in sorted(list_duplicates(result)):
        print dup


        corpus = []
        categoried_file_names = []
        fullpath_file_names = []
        for idx in dup[1]:
            fullpath_file_names.append(filtered_file_name[idx])
            categoried_file_name = basename(filtered_file_name[idx])
            corpus.append(bow_docs[categoried_file_name])
            categoried_file_names.append(categoried_file_name)

        cluster_result_doc[str(dup[0])] = ",".join(categoried_file_names).encode('utf-8')

        topics = get_topics(corpus, dct)
        # topics = get_terms('lr', ",".join(fullpath_file_names).encode('utf-8'))
        cluster_result_word[str(dup[0])] = ",".join(topics).decode('utf-8')

        outputfilename = str(dup[0])
        with open(outputfilename+'.json', 'wb') as outfile:
            json.dump(topics, outfile)
        word_cloud.create_wordcloud(" ".join(topics).decode('utf-8'), outputfilename)

    with open('documents.json', 'wb') as outfile:
        json.dump(cluster_result_doc, outfile)

    with open('attribute2.json', 'wb') as outfile:
        json.dump(cluster_result_word, outfile)

    pass

# cluster_docs('elbow_analysis')