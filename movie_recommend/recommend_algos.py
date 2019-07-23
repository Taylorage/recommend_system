from scipy.stats import pearsonr
from scipy.spatial.distance import cosine  # 余弦距离，1-余弦值

import numpy as np
import unicodedata
import copy
import math


def sim(x, y, metric='cos'):
	"""相似度计算"""
	if metric == 'cos':
		return 1 - cosine(x,y)
	else:
		return pearsonr(x,y)[0]

# 基于物品的协同过滤算法
class CF_itembased(object):
	"""
	算法思想：
	1. 找出与用户i打过分的商品最相似的K件商品
	2. 计算K件商品的打分的加权均值，作为预测值
	"""
	def __init__(self, data):
		"""
		构造函数，计算物品相似度矩阵
		data为用户物品打分矩阵
		"""
		nitems = len(data[0])
		self.data = data
		self.simmatrix = np.zeros((nitems, nitems))
		for i in range(nitems):
			for j in range(nitems):
				if j >= i: # 右上角
					self.simmatrix[i,j] = sim(data[:,i], data[:,j])
				else:
					self.simmatrix[i,j] = self.simmatrix[j,i]

	def GetKSimItemPerUser(self, r, K, u_vec):
		"""
		找出与给定商品最相似的,用户打过分的K个商品
		r：目标商品索引
		K：近邻数量
		u_vec:目标用户打分向量
		"""
		items = np.argsort(self.simmatrix[r])[::-1] # r列，从大到小排
		items = items[items!=r]
		cnt = 0
		neighitems = []
		for i in items:
			if u_vec[i] > 0 and cnt < K:
				neighitems.append(i)
				cnt += 1
			elif cnt == K:
				break
		return neighitems

	def CalcRating(self, r, u_vec, neighitems):
		"""
		根据相似度和已有物品的打分，计算目标物品的预测分数
		若未找到近邻，设置为自己的均分
		"""
		rating = 0.
		den = 0.
		for i in neighitems:
			rating += self.simmatrix[r, i]*u_vec[i] # 物品r和i的相似度分数*用户对i的打分
			den += abs(self.simmatrix[r,i])
		if den > 0:
			rating = np.round(rating/den, 0) # 取整
		else:
			rating = np.round(self.data[:,r][self.data[:,r]>0].mean(), 0)

	def CalcRatings(self, u_vec, K):
		"""
		对目标用户所有未打过分的物品进行预测
		根据预测分数，给出推荐列表
		"""
		u_rec = copy.copy(u_vec)
		for r in range(len(u_vec)): 
			if u_vec[r] == 0: # 对未打过分的物品，找出K近邻，预测
				neighitems = self.GetKSimItemPerUser(r, K, u_vec) # 找出近邻
				u_rec[r] = self.CalcRating(r,u_vec,neighitems) # 根据近邻预测
		seenindxs = [indx for indx in range(len(u_vec)) if u_vec[indx]>0]
		u_rec[seenindxs] = -1
		recsvec = np.argsort(u_rec)[::-1][np.argsort(u_rec)>0] # 根据预测分数给出推荐
		return recsvec




