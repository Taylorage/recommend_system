from django.db import models
from django.contrib.auth.models import User
import jsonfield
import json
import numpy as np


class UserProfile(models.Model):

	user = models.ForeignKey(User, unique=True,on_delete=models.CASCADE) # 用户
	array = jsonfield.JSONField() # 用户对电影的打分向量
	arrayratedmoviesindxs = jsonfield.JSONField() # 打过分的电影索引
	name = models.CharField(max_length=100) # 电影名
	lastrecs = jsonfield.JSONField() # 上次推荐结果

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		create = kwargs.pop('create', None)
		recsvec = kwargs.pop('recsvec', []) # None难判断
		if create: # 新注册用户
			super(UserProfile, self).save(*args, **kwargs)
		elif len(recsvec) != 0: # 上次推荐结果
		# 空数组的真值是不明确的 https://blog.csdn.net/u010899985/article/details/80514316
			self.lastrecs = json.dumps(recsvec.tolist())
			super(UserProfile, self).save(*args, **kwargs)
		else: # 老用户
			nmovies = MovieData.objects.count()
			array = np.zeros(nmovies)
			ratedmovies = self.ratedmovies.all() # 根据用户查询其打过分的电影（self.ratedmovies来自MovieRated）
			# 外键使用：https://blog.csdn.net/hpu_yly_bj/article/details/78939748
			self.arrayratedmoviesindxs = json.dumps([m.movieindx for m in ratedmovies])
			for m in ratedmovies:
				array[m.movieindx] = m.value 
			self.array = json.dumps(array.tolist())
			super(UserProfile, self).save(*args, **kwargs)

class MovieRated(models.Model):

	user = models.ForeignKey(UserProfile, related_name = 'ratedmovies',on_delete=models.CASCADE) # 用户
	movie = models.CharField(max_length=100) # 电影
	movieindx = models.IntegerField(default=-1) # 电影索引
	value = models.IntegerField() # 打分值

	def __str__(self):
		return self.movie

class MovieData(models.Model):
	title = models.CharField(max_length=100) # 电影名
	array = jsonfield.JSONField() # 向量表示
	ndim = models.IntegerField(default=300) # 维度
	description = models.TextField() # 电影简介






