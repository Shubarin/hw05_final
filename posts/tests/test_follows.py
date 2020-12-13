from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post, User


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unfollow_user = User.objects.create(
            username='unfollow_username',
            email='unfollow_username@testmail.com',
        )
        cls.user = User.objects.create(
            username='testusername',
            email='testusername@testmail.com',
        )
        cls.author = User.objects.create(
            username='testauthor',
            email='testauthor@testmail.com',
        )
        cls.group = Group.objects.create(
            title='Тестовое сообщество',
            slug='test-slug',
            description='test description'
        )
        cls.post = Post.objects.create(
            text='Заголовок тестовой записи',
            author=cls.author,
            group=cls.group,
        )
        cls.post_id = cls.post.id

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(FollowTests.user)
        self.authorized_unfollow_client = Client()
        self.authorized_unfollow_client.force_login(FollowTests.unfollow_user)
        self.guest_client = Client()
        cache.clear()

    def test_authorize_user_follow_other_users(self):
        """
        Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок
        """
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': FollowTests.author}))
        user = response.context.get('user')
        # Считаем подписчиков до подписки
        followers_before = Follow.objects.filter(
            author=FollowTests.author).count()
        # Подписываем авторизованного пользователя на автора
        follow = Follow.objects.create(
            user=user,
            author=FollowTests.author
        )
        # Считаем подписчиков после подписки
        followers_after = Follow.objects.filter(
            author=FollowTests.author).count()
        self.assertEqual(followers_before + 1, followers_after)
        # Удаляем подписку
        follow.delete()
        # Считаем подписчиков после удаления подписки
        followers_after_delete = Follow.objects.filter(
            author=FollowTests.author).count()
        self.assertEqual(followers_before, followers_after_delete)

    def test_new_post_author_add_followers(self):
        """
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех,
        кто не подписан на него.
        """
        # Подписываем авторизованного пользователя на автора
        Follow.objects.create(
            user=FollowTests.user,
            author=FollowTests.author
        )
        # Получаем содержимое страницы для неподписанного пользователя
        response_unfollow = self.authorized_unfollow_client.get(
            reverse('posts:follow_index'))
        page_unfollow_user_before = response_unfollow.content
        # Получаем содержимое страницы после подписки
        response_follower = self.authorized_client.get(
            reverse('posts:follow_index'))
        page_before_new_post = len(response_follower.context.get('page'))
        # Создаем новый пост автора и очищаем кэш
        Post.objects.create(
            text='Новый пост от автора',
            author=FollowTests.author
        )
        cache.clear()
        # Получаем содержимое страницы после добавления записи
        response_follower = self.authorized_client.get(
            reverse('posts:follow_index'))
        page_after_new_post = len(response_follower.context.get('page'))
        # Получаем содержимое страницы для неподписанного пользователя
        response_unfollow = self.authorized_unfollow_client.get(
            reverse('posts:follow_index'))
        page_unfollow_user_after = response_unfollow.content
        self.assertEqual(page_before_new_post + 1, page_after_new_post)
        self.assertEqual(page_unfollow_user_before, page_unfollow_user_after)

    def test_only_an_authorized_user_can_comment_on_posts(self):
        """Только авторизированный пользователь может комментировать посты"""
        form_data = {
            'text': 'test_text',
            'author': FollowTests.user,
            'post': FollowTests.post,
        }
        comments_count_before = Comment.objects.count()
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={
                'username': FollowTests.post.author.username,
                'post_id': FollowTests.post_id
            }), data=form_data, follow=True, )
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={
                'username': FollowTests.post.author.username,
                'post_id': FollowTests.post_id
            }), data=form_data, follow=True, )
        comments_count_after = Comment.objects.count()
        self.assertEqual(comments_count_before + 1, comments_count_after)
