"""recommend_system URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
import movie_recommend.views


urlpatterns = [
	path('', movie_recommend.views.home, name='home'), # 主页
	path('auth/',movie_recommend.views.auth, name = 'auth'), # 注册登录
	path('signout/', movie_recommend.views.signout, name = 'signout'), # 登出
    path('rate_movie/',movie_recommend.views.rate_movie, name = 'rate_movie'), # 打分（在查询结果页面）
    path('movies-recs/', movie_recommend.views.movies_recs, name= 'movies_recs'), # 推荐（base.html）
	path('admin/', admin.site.urls), # 后台管理
]
