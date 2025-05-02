from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'game'

urlpatterns = [
    # Game
    path('play/',         views.play_view,          name='play'),
    path('leaderboard/',  views.leaderboard_view,   name='leaderboard'),
    path('profile/',      views.profile_view,       name='profile'),
    path('api/run/',      views.run_trial,          name='run_trial'),
    path('quests/',             views.quest_list_view,      name='quest_list'),
    path('quests/<int:quest_id>/',     views.quest_detail_view,    name='quest_detail'),
    path('quests/<int:quest_id>/advance/', views.quest_advance_view,   name='quest_advance'),
    path('buy_hint/', views.buy_hint, name='buy_hint'),

    # Authentication
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
]
