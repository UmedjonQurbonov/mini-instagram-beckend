from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.models import User
from accounts.serializers import UserBasicSerializer
from .models import *
from .serializers import *
from .permissions import IsOwnerOrReadOnly, IsCommentOwnerOrReadOnly
from rest_framework.views import APIView

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class FollowViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    
    @action(detail=True, methods=['post'])
    def follow_toggle(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)

        if request.user == user:
            return Response(
                {'detail': 'You cannot follow yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        follow = Follow.objects.filter(
            follower=request.user,
            following=user
        )

        if follow.exists():
            follow.delete()
            return Response(
                {'detail': 'Unfollowed.'},
                status=status.HTTP_204_NO_CONTENT
            )

        Follow.objects.create(
            follower=request.user,
            following=user
        )
        return Response(
            {'detail': 'Followed.'},
            status=status.HTTP_201_CREATED
        )
    


class FollowersListView(generics.ListAPIView):
    serializer_class = UserBasicSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user_id = self.kwargs.get('pk')
        user = get_object_or_404(User, pk=user_id)
        follower_ids = user.followers.values_list('follower', flat=True)
        return User.objects.filter(id__in=follower_ids).select_related('profile')


class FollowingListView(generics.ListAPIView):
    serializer_class = UserBasicSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user_id = self.kwargs.get('pk')
        user = get_object_or_404(User, pk=user_id)
        following_ids = user.following.values_list('following', flat=True)
        return User.objects.filter(id__in=following_ids).select_related('profile')


class PostViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['author']
    search_fields = ['caption']
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return Post.objects.filter(is_deleted=False).select_related(
            'author', 'author__profile'
        ).prefetch_related('likes', 'comments')
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PostCreateUpdateSerializer
        return PostSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        return [IsAuthenticated()]
    
    def list(self, request, *args, **kwargs):
        cache_key = f'posts_list_{request.GET.urlencode()}'
        print(cache_key)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, 60)
        return response
    
    def retrieve(self, request, *args, **kwargs):
        cache_key = f'post_{kwargs.get("pk")}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, 60)
        return response
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        
        cache_key = f'post_{instance.id}'
        cache.delete(cache_key)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def followings(self, request):
        following_ids = request.user.following.values_list('following', flat=True)
        
        queryset = Post.objects.filter(
            author__id__in=following_ids,
            is_deleted=False
        ).select_related('author', 'author__profile').prefetch_related('likes', 'comments')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path=r'user/(?P<user_id>\d+)')
    def user_posts(self, request, user_id=None):
        user = get_object_or_404(User, pk=user_id)

        queryset = Post.objects.filter(author=user, is_deleted=False).select_related('author', 'author__profile').prefetch_related('likes', 'comments')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        post_id = self.kwargs.get('post_pk')
        return Comment.objects.filter(post_id=post_id).select_related(
            'author', 'author__profile'
        )
    
    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), IsCommentOwnerOrReadOnly()]
        return [IsAuthenticated()]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        cache_key = f'post_{instance.post.id}'
        cache.delete(cache_key)
        
        return super().destroy(request, *args, **kwargs)

class PostLikeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk, is_deleted=False)

        like, created = Like.objects.get_or_create(
            user=request.user,
            post=post
        )

        if created:
            return Response(
                {'detail': 'Post liked'},
                status=status.HTTP_201_CREATED
            )

        like.delete()
        return Response(
            {'detail': 'Post unliked'},
            status=status.HTTP_204_NO_CONTENT
        )    