from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')

urlpatterns = [
    path('users/<int:pk>/follow/', FollowViewSet.as_view({'post': 'follow'}), name='follow'),
    path('users/<int:pk>/unfollow/', FollowViewSet.as_view({'post': 'unfollow'}), name='unfollow'),
    path('users/<int:pk>/followers/', FollowersListView.as_view(), name='followers-list'),
    path('users/<int:pk>/following/', FollowingListView.as_view(), name='following-list'),
    path('', include(router.urls)),
    path('posts/<int:post_pk>/comments/', CommentViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='comment-list'),
    path('posts/<int:post_pk>/comments/<int:pk>/', CommentViewSet.as_view({
        'get': 'retrieve',
        'delete': 'destroy'
    }), name='comment-detail'),
    path('posts/<int:pk>/like/', PostLikeAPIView.as_view(), name='post-like'),

]