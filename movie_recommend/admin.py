from django.contrib import admin
from movie_recommend.models import MovieData, UserProfile

class MoviesAdmin(admin.ModelAdmin):
	list_display = ['title', 'description'] # 该字段负责修改文章默认显示的字段；默认只显示标题

# 向后台注册models.py中的模型，如果不注册，admin后台将无法识别
admin.site.register(UserProfile)
admin.site.register(MovieData,MoviesAdmin)
