from rest_framework import serializers
from .models import *
from accounts.serializers import UserBasicSerializer


class FollowSerializer(serializers.ModelSerializer):
    follower = UserBasicSerializer(read_only=True)
    following = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Follow
        fields = ('id', 'follower', 'following', 'created_at')
        read_only_fields = fields


class CommentSerializer(serializers.ModelSerializer):
    author = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ('id', 'post', 'author', 'text', 'created_at')
        read_only_fields = ('id', 'author', 'created_at')
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class PostSerializer(serializers.ModelSerializer):
    author = UserBasicSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = ('id', 'author', 'image', 'caption', 'created_at', 'updated_at', 'likes_count', 'comments_count', 'comments', 'is_liked')
        read_only_fields = ('id', 'author', 'created_at', 'updated_at', 'likes_count', 'comments_count', 'is_liked')
    
        def get_likes_count(self, obj):
            return obj.likes.count()
    
    def get_comments_count(self, obj):
        return obj.comments.count()
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.parser_context.get('view').action == 'list':
            data.pop('comments', None)
        return data
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ('image', 'caption')
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
    

class EmptySerializer(serializers.Serializer):
    pass