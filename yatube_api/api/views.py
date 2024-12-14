from rest_framework import viewsets, mixins, filters
from rest_framework.exceptions import ValidationError, PermissionDenied
from posts.models import Post, Group, Comment, Follow
from .serializers import GroupSerializer, CommentSerializer, FollowSerializer
from .serializers import PostSerializer
from rest_framework.pagination import LimitOffsetPagination
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated


class FollowViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    serializer_class = FollowSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (filters.SearchFilter,)
    search_fields = ['user__username', 'following__username']

    def get_queryset(self):
        # Показываем только подписки текущего пользователя
        return Follow.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        following = serializer.validated_data['following']
        # Проверяем, чтобы пользователь не подписывался на самого себя
        if user == following:
            raise ValidationError("Нельзя подписаться на самого себя.")
        # Проверяем, чтобы подписка была уникальной
        if Follow.objects.filter(user=user, following=following).exists():
            raise ValidationError("Вы уже подписаны на этого пользователя.")
        serializer.save(user=user)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    pagination_class = LimitOffsetPagination

    def perform_create(self, serializer):
        # Добавляем текущего пользователя как автора
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        # Проверка на авторство перед обновлением
        if serializer.instance.author != self.request.user:
            raise PermissionDenied('Изменение чужого контента запрещено!')
        super(PostViewSet, self).perform_update(serializer)

    def perform_destroy(self, instance):
        # Проверка, что только автор комментария может его удалить
        if instance.author != self.request.user:
            raise PermissionDenied('Вы не можете удалить чужой пост')
        # Если пользователь — автор, выполняем удаление
        instance.delete()


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer

    def get_queryset(self):
        post_id = self.kwargs.get('post_id')
        return Comment.objects.filter(post_id=post_id)

    def perform_create(self, serializer):
        post_id = self.kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        serializer.save(post=post, author=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user:
            raise PermissionDenied('Изменение чужого контента запрещено!')
        super(CommentViewSet, self).perform_update(serializer)

    def perform_destroy(self, instance):
        # Проверка, что только автор комментария может его удалить
        if instance.author != self.request.user:
            raise PermissionDenied('Вы не можете удалить чужой комментарий.')
        # Если пользователь — автор, выполняем удаление
        instance.delete()
