from django.urls import path , include

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:doc_id>/', views.detail, name="detail"),
    path('download/<int:doc_id>/', views.download, name="download"),
    path('search/', views.HighlightedSearchView(), name="search"),
    path('search/<int:search_id>/', views.search_results, name="search_results"),
    path('all_searches/', views.all_searches, name="all_searches"),
    path('search_native/', include('haystack.urls')),
]