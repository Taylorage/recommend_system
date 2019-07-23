import pandas as pd
import numpy as np
import json
from sklearn.feature_extraction.text import TfidfVectorizer

from movie_recommend.models import MovieData
from django.core.cache import cache

import os
BASE_DIR = os.path.dirname(os.path.abspath('__file__'))
PATH = os.path.join(BASE_DIR, 'plots.csv')
N_MAX_WORDS = 30000

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import WordPunctTokenizer
tknzr = WordPunctTokenizer()
#nltk.download('stopwords')
stoplist = stopwords.words('english')
from nltk.stem.porter import PorterStemmer
stemmer = PorterStemmer()


def PreprocessTfidf(texts, stoplists=[], stem=False):
	newtexts = []
	for i in range(len(texts)):
		text = texts[i]
		if stem:
			tmp = [w for w in tknzr.tokenize(text) if w not in stoplist]
		else:
			tmp = [stemmer.stem(w) for w in tknzr.tokenize(text) if w not in stoplist]
		newtexts.append(' '.join(tmp))
	return newtexts

def load_data():
	"""
	加载电影信息数据,存入数据模型和缓存
	"""
	df = pd.read_csv(open(PATH))
	plots = df['plot'].tolist()
	titles = df['title'].tolist()
	vectorizer = TfidfVectorizer(min_df=0, max_features=N_MAX_WORDS)
	processed_plots = PreprocessTfidf(plots, stoplist, True)
	mod_idf = vectorizer.fit(processed_plots)
	vec_tfidf = mod_idf.transform(processed_plots)
	ndims = len(mod_idf.get_feature_names())
	nmovies = len(titles[:])

	MovieData.objects.all().delete()
	matr = np.empty([1, ndims])
	titles_list = []
	cnt = 0
	for m in range(nmovies):
		moviedata = MovieData()
		moviedata.title = titles[m]
		moviedata.description = plots[m]
		moviedata.ndim = ndims
		moviedata.array = json.dumps(vec_tfidf[m].toarray()[0].tolist())
		moviedata.save()

		newrow = vec_tfidf[m].toarray()[0].tolist()
		if cnt == 0:
			matr[0] = newrow
		else:
			matr = np.vstack([matr, newrow])
		titles_list.append(moviedata.title)
		cnt += 1
	cache.set('data', matr)
	cache.set('titles', titles_list)
	cache.set('model', mod_idf)
	print('load MovieData to cache')
	# 加载用户电影打分矩阵
	df_umatrix = pd.read_csv(open(os.path.join(BASE_DIR, 'umatrix.csv')))
	Umatrix = df_umatrix.values[:,1:]
	cache.set('umatrix', Umatrix)
	print('load umatrix to cache……')

if __name__ == "__main__":
	load_data()



