from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    title = models.CharField(
        max_length=200,
        verbose_name='Сообщество',
        help_text='Выберите название сообщества',
    )
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(max_length=400)

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(
        verbose_name='Текст сообщения',
        help_text='Напишите текст вашего сообщения'
    )
    pub_date = models.DateTimeField("date published", auto_now_add=True,
                                    db_index=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    group = models.ForeignKey(
        Group,
        verbose_name='Сообщество',
        help_text='Выберите название сообщества',
        on_delete=models.SET_NULL,
        related_name='posts',
        blank=True,
        null=True,
    )
    image = models.ImageField(upload_to='posts/', blank=True, null=True)

    class Meta:
        ordering = ['-pub_date']

    def __str__(self):
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        verbose_name='Пост',
        help_text='Текст поста',
        on_delete=models.CASCADE,
        related_name="comments",
        blank=True,
        null=True,
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    text = models.TextField(
        verbose_name='Текст комментария',
        help_text='Напишите текст вашего комментария',
        max_length=400,
    )
    created = models.DateTimeField("date created", auto_now_add=True)

    class Meta:
        ordering = ['-created']


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )

    class Meta:
        unique_together = ['user', 'author']