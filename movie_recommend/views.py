from django.shortcuts import render # 渲染页面
from django.shortcuts import redirect
#from django.core.urlresolvers import reverse
from django.urls import reverse
import urllib
from ast import literal_eval

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login # 处理登录和退出
from django.contrib.auth import logout
from django.core.cache import cache 

from movie_recommend.models import MovieData, MovieRated, UserProfile # 数据模型
from movie_recommend.recommend_algos import *  # 推荐算法模块
from movie_recommend.load_data import *

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import os
BASE_DIR = os.path.dirname(os.path.abspath('__file__'))
PATH = os.path.join(BASE_DIR, 'umatrix.csv') # 电影评分矩阵的文件路径
NMOVIES = 5
N_MIN_RATES = 5 # 推荐要求用户打过分电影的最低数量
RECS_METHOD = 'cf_itembased' # 推荐算法
NUM_RECS = 5 # 给用户推荐的电影数

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import WordPunctTokenizer
tknzr = WordPunctTokenizer()
#nltk.download('stopwords') # 第一次需下载停用词
stoplist = stopwords.words('english')
from nltk.stem.porter import PorterStemmer # 波特词干算法

def Preprocesstfidf(texts, stoplist=[], stem=False):
	# 预处理电影信息，去停用词
	newtexts = []
	for text in texts:
		if stem:
			tmp = [w for w in tknzr.tokenize(text) if w not in stoplist]
		else:
			tmp = [stemmer.stem(w) for w in tknzr.tokenize(text) if w not in stoplist]
		newtexts.append(' '.join(tmp))
	return newtexts

# 电影检索模块：根据用户查询词，给出电影列表
"""
用户在搜索框输入查询词，点击搜索按钮，触发home函数
home函数获取查询词，POST方法重定向到GET方法
根据查询词，从缓存中调取电影信息数据：电影向量矩阵，TF-IDF模型
TF-IDF模型将查询词向量化
计算查询词和电影向量矩阵的相似度，根据相似度返回查询结果
展示电影名称和后面的分数[1,2,3,4,5]供用户打分
"""
def home(request):
	
	context = {}
	# 登录后的搜索页面,POST方法将请求转交给GET方法处理
	if request.method == 'POST': 
		post_data = request.POST
		data = {}
		data = post_data.get('data',None) # 获取用户输入的查询词
		if data:
			return redirect('%s?%s' % (reverse('home'),
			urllib.parse.urlencode({'q':data}))) # reverse逆向解析出url，重定向到查询过程，传参数：查询词data
		else:
			return render(request, 'movie_recommend/home.html',context)

	# 进入搜索,获取查询词，从缓存加载数据，进行相似度计算，返回电影列表
	elif request.method == 'GET':
		get_data = request.GET
		data = get_data.get('q', None) # 获取查询词
		titles = cache.get('titles') # 从缓存获取标题

		# 检查缓存中是否已加载电影标题，没有就加载
		if not titles:
			print ('load data to cache……')
			load_data() # 加载电影数据到数据模型MovieData和缓存中
			texts = [] # 电影信息列表
			mobjs = MovieData.objects.all()
			ndim = mobjs[0].ndim
			matr = np.empty([1, ndim]) # 电影向量矩阵
			titles_list = [] # 电影标题列表
			cnt = 0
			for obj in mobjs[:]:
				texts.append(obj.description)
				newrow = np.array(obj.array)
				if cnt == 0:
					matr[0] = newrow
				else:
					matr = np.vstack([matr,newrow]) # 垂直拼接
				titles_list.append(obj.title)
				cnt += 1
			vectorizer = TfidfVectorizer(min_df=1, max_features=ndim)
			processedtexts = PreprocessTfidf(texts, stoplist, True) # 预处理，去停用词
			model = vectorizer.fit(processedtexts) # 对电影简介进行训练

			cache.set('model',model) 
			cahce.set('data', matr)
			cahce.set('titles', titles_list)

		else:
			print ('data loaded')

		Umatrix = cache.get('umatrix') # 从缓存中加载用户电影评分矩阵
		if Umatrix.size == 0:
			# 空数组的真值是不明确的 https://blog.csdn.net/u010899985/article/details/80514316
			df_umatrix = pd.read_csv(open(PATH))
			print('load umatrix……')
			Umatrix = df_umatrix.values[:,1:]
			print ('umatrix',Umatrix.shape)
			cache.set('umatrix', Umatrix) # 将打分矩阵加入缓存
			cf_itembased = CF_itembased(Umatrix) # 基于物品的协同过滤算法，模块导入
			cache.set('cf_itembased', cf_itembased)

		# 检查查询词，空查询词跳转主页
		if not data:
			return render(request, 'movie_recommend/home.html',context)

		# command文件夹的load_data命令将模型加载到缓存后
		# 将用户查询词转为TF-IDF向量
		# 从缓存中查找与查询词向量相似的电影列表（根据电影标题）
		matr = cache.get('data') # 电影信息向量矩阵,matr由array堆叠而成，array来自MovieData对象
		titles = cache.get('titles')
		model_tfidf = cache.get('model')
		# 将查询词转为向量
		queryvec = model_tfidf.transform([data.lower().encode('ascii', 'ignore')]).toarray()
		sims = cosine_similarity(queryvec, matr)[0] # 计算相似度
		indxs_sims = list(sims.argsort())[::-1]
		titles_query = list(np.array(titles)[indxs_sims][:NMOVIES]) # 返回电影标题列表
		# 装入context，渲染展示
		context['movies'] = list(zip(titles_query, indxs_sims[:NMOVIES]))
		#print('测试：',list(zip(titles_query, indxs_sims[:NMOVIES])))
		context['rates'] = [1,2,3,4,5]
		return render(request, 'movie_recommend/query_results.html',context) # 查询结果页面

# 注册和登录模块
"""
用户点击页面顶部的注册或登录按钮时，会触发auth函数
auth函数根据点击的是注册还是登录按钮，跳转不同的页面
跳转后获取用户名和密码，是否是新用户的标识create
若是注册，验证用户名是否已存在。新建用户，并在数据表新增一条用户记录，登录后返回主页
若登录，验证用户是否有效。登录后返回主页
"""
def auth(request):
	# 点击注册和登录按钮时
	if request.method == 'GET': 
		data = request.GET
		auth_method = data.get('auth_method')
		if auth_method=='登录': # 按不同按钮，跳转到不同页面
			return render(request,'movie_recommend/signin.html', {}) # 跳转登录页面
		else:
			return render(request,'movie_recommend/createuser.html', {}) # 注册页面
	# 注册或登录页面输入用户名和密码
	elif request.method == 'POST':
		post_data = request.POST
		name = post_data.get('name',None) # 用户名
		pwd = post_data.get('pwd',None) # 密码
		pwd1 = post_data.get('pwd1',None) # 注册时第二次输入密码，登录时为空
		create = post_data.get('create',None) # 新建议用户与否，登录为空
		# 新建用户注册并登录
		if name and pwd and create:
			# 用户名已存在或注册时两次密码不一致
			if User.objects.filter(username=name).exists() or pwd !=pwd1:
				return render(request, 'movie_recommend/userexistsorproblem.html',{})  # 报错页面
			user = User.objects.create_user(username=name,password=pwd)
			uprofile = UserProfile() # 数据库新建一条用户记录
			uprofile.user = user
			uprofile.name = user.username
			uprofile.save(create=True)

			user = authenticate(username=name,password=pwd) # 验证用户信息，返回User对象
			login(request, user) # 登录
			return render(request, 'movie_recommend/home.html', {}) # 返回主页
		# 老用户登录
		elif name and pwd:
			user = authenticate(username=name,password=pwd)
			if user: # 有效用户
				login(request, user)
				return render(request, 'movie_recommend/home.html', {}) # 登录后跳转主页
			else:
				return render(request, 'movie_recommend/nopersonfound.html', {}) # 无效用户，报错
# 登出模块
def signout(request):
	logout(request) # 登出
	return render(request, 'movie_recommend/home.html', {}) # 跳转到主页


# 打分模块
"""
在查询结果页面，用户点击每部电影后面的分数，会触发打分函数
打分函数获取到用户打分的电影和分数，更新或新增数据库，返回剩下未打分的电影
"""
def RemoveFromList(liststrings, string):
	outlist = []
	for s in liststrings:
		if s == string:
			continue
		outlist.append(s)
	return outlist

def rate_movie(request):
	"""
	获取用户打分信息，存入数据库
	"""
	data = request.GET
	rate = data.get('vote') # 获取分数
	#print('测试：分数:',rate)
	#print('测试：data.get("movies")',data.get("movies"))
	#print('测试：data.get("movies")',list(zip(*literal_eval(data.get("movies")))))
	movies, moviesindxs = list(zip(*literal_eval(data.get("movies")))) # data.get("movies")得到的是字符串的列表'[]'
	# literal_eval实现从元祖，列表，字典型的字符串到元祖，列表，字典的转换
	movie = data.get('movie')
	movieindx = int(data.get('movieindx'))

	userprofile = None
	# 区分用户状态
	if request.user.is_superuser:
		return render(request, 'movie_recommend/superusersignin.html', {})
	elif request.user.is_authenticated:
		userprofile = UserProfile.objects.get(user=request.user) # 调取登录用户的档案
	else:
		return render(request, 'movie_recommend/pleasesignin.html', {})

	# 存入数据库，更新或新增
	if MovieRated.objects.filter(movie=movie).filter(user=userprofile).exists():
		mr = MovieRated.objects.get(movie=movie, user=userprofile)
		mr.value = int(rate)
		mr.save()
	else:
		mr = MovieRated() # 用户，分数，电影名，电影索引
		mr.user = userprofile
		mr.value = int(rate)
		mr.movie = movie
		mr.movieindx = movieindx
		mr.save()
	userprofile.save() # 更新array
	# 删除打过分的电影
	movies = RemoveFromList(movies, movie)
	moviesindxs = RemoveFromList(moviesindxs, movieindx)
	# 展示剩下的电影
	context = {}
	context['movies'] = list(zip(movies, moviesindxs)) # python3返回的是迭代器，需转为列表
	context['rates'] = [1,2,3,4,5]
	return render(request, 'movie_recommend/query_results.html',context)

# 推荐模块
"""
对某个特定个用户，给出一个电影列表：
1. 调取用户信息，获取其历史打分记录，检查数量是否满足最低要求
2. 从缓存调取所有用户的打分矩阵和所有电影名称，输入推荐算法，给出推荐结果
"""
def movies_recs(request):

	userprofile = None
	# 区分用户
	if request.user.is_superuser:
		return render(request, 'movie_recommend/superusersignin.html', {})
	elif request.user.is_authenticated:
		userprofile = UserProfile.objects.get(user=request.user) # 调取登录用户的档案
	else:
		return render(request, 'movie_recommend/pleasesignin.html', {})

	ratedmovies = userprofile.ratedmovies.all() # 取出用户所有打过分的电影
	# 外键的使用：https://blog.csdn.net/hpu_yly_bj/article/details/78939748
	context = {}
	if len(ratedmovies) < N_MIN_RATES:
		context['nrates'] = len(ratedmovies)
		context['n_min_rates'] = N_MIN_RATES
		return render(request, 'movie_recommend/underminimum.html', context)

	u_vec = np.array(list(literal_eval(userprofile.array)))
	# https://stackoverflow.com/questions/48643256/typeerror-iteration-over-a-0-d-array-python
	#print('测试：u_vec',u_vec.shape)
	Umatrix = cache.get('umatrix')
	movieslist = cache.get('titles')
	# 推荐算法给出推荐结果
	u_rec = None
	if RECS_METHOD == 'cf_itembased':
		cf_itembased = cache.get('cf_itembased')
		if not cf_itembased:
			cf_itembased = CF_itembased(Umatrix)
		u_rec = cf_itembased.CalcRatings(u_vec, NUM_RECS) # 计算推荐结果
		#print('推荐结果u_rec：',u_rec)
	elif RECS_METHOD == 'cf_userbased':
		u_rec = CF_userbased(u_vec, NUM_RECS, Umatrix)

	userprofile.save(recsvec=u_rec) # 存入数据库
	context['recs'] = list(np.array(movieslist)[list(u_rec)][:NUM_RECS]) 
	return render(request, 'movie_recommend/recommendations.html',context) # 展示推荐结果








