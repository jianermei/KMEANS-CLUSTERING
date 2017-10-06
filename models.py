from app import db
from sqlalchemy.dialects.postgresql import JSON


class Result(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String())
    result_all = db.Column(JSON)
    result_no_stop_words = db.Column(JSON)
    cluster_number_start = db.Column(db.Integer)
    cluster_number_end = db.Column(db.Integer)
    silhouette_scores = db.Column(JSON)
    word_lists = db.Column(JSON)

    def __init__(self, url, result_all, result_no_stop_words, cluster_number_start, cluster_number_end, silhouette_scores, word_lists):
        self.url = url
        self.result_all = result_all
        self.result_no_stop_words = result_no_stop_words
        self.cluster_number_start = cluster_number_start
        self.cluster_number_end = cluster_number_end
        self.silhouette_scores = silhouette_scores
        self.word_lists = word_lists

    def __repr__(self):
        return '<id {}>'.format(self.id)