from django.contrib import admin
from django.urls import path, include
from game import views as game_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', game_views.home, name='home'),

    # All game-related URLs now live under /game/…
    path('game/', include('game.urls', namespace='game')),
]
