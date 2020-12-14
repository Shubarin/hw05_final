import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post, User
from yatube.settings import RECORDS_ON_THE_PAGE


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=tempfile.gettempdir())
        # Создадим запись в БД
        cls.user = User.objects.create(
            username='testusername',
            email='testusername@testmail.com',
        )
        cls.group = Group.objects.create(
            title='Тестовое сообщество',
            slug='test-slug',
            description='test description'
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Заголовок тестовой записи',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.post_id = cls.post.id

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'index.html': reverse('posts:index'),
            'new_post.html': reverse('posts:new_post'),
            'group.html': (
                reverse('posts:blogs', kwargs={'slug': 'test-slug'})
            ),
            'profile.html': (
                reverse('posts:profile', kwargs={'username': 'testusername'})
            ),
            'post.html': (
                reverse('posts:post', kwargs={'username': 'testusername',
                                              'post_id': PostPagesTests.post_id})
            ),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_edit_page_uses_correct_template(self):
        template = 'new_post.html'
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'username': 'testusername',
                                               'post_id': PostPagesTests.post_id}))
        self.assertTemplateUsed(response, template)

    def test_new_post_page_show_correct_context(self):
        """Шаблон new_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:new_post'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_index_page_show_correct_context(self):
        """
        Шаблон index сформирован с правильным контекстом.
        и при создании поста этот пост появляется на главной странице сайта
        """
        response = self.authorized_client.get(reverse('posts:index'))
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        post_text_0 = response.context.get('page')[0].text
        post_author_0 = response.context.get('page')[0].author
        post_group_0 = response.context.get('page')[0].group
        post_image_0 = response.context.get('page')[0].image
        self.assertEqual(post_text_0, 'Заголовок тестовой записи')
        self.assertEqual(post_author_0, PostPagesTests.user)
        self.assertEqual(post_group_0, PostPagesTests.group)
        # сравниваем битовое представление изображений
        with open(str(post_image_0.file), 'rb') as post_image_bytes:
            self.assertEqual(post_image_bytes.read(), PostPagesTests.small_gif)

    def test_blogs_detail_pages_show_correct_context(self):
        """
        Шаблон blogs сформирован с правильным контекстом.
        Новый пост появляется на странице выбранной группы
        """
        response = self.authorized_client.get(
            reverse('posts:blogs', kwargs={'slug': 'test-slug'})
        )
        self.assertEqual(response.context.get('group').title,
                         'Тестовое сообщество')
        self.assertEqual(response.context.get('group').description,
                         'test description')
        self.assertEqual(response.context.get('group').slug, 'test-slug')

    def test_profile_pages_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'testusername'})
        )
        self.assertEqual(response.context.get('profile_user'),
                         PostPagesTests.user)
        self.assertEqual(response.context.get('user_post_count'), 1)

    def test_cache_index_page_show_correct_context(self):
        # Получаем контент страницы
        response_before = self.authorized_client.get(reverse('posts:index'))
        page_before_clear_cache = response_before.content
        # Меняем пост в БД
        post = Post.objects.latest('id')
        post.text = 'Upd ' + post.text
        post.save()
        # Получаем контент страницы после обновления
        response_before = self.authorized_client.get(reverse('posts:index'))
        page_before_clear_cache_refresh = response_before.content
        self.assertEqual(page_before_clear_cache,
                         page_before_clear_cache_refresh)
        # После очистки кэша страницы будут отличатся
        cache.clear()
        response_after = self.authorized_client.get(reverse('posts:index'))
        page_after_clear_cache = response_after.content
        self.assertNotEqual(page_before_clear_cache, page_after_clear_cache)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД
        cls.user = User.objects.create(
            username='testusername',
            email='testusername@testmail.com',
        )
        cls.group = Group.objects.create(
            title='Тестовое сообщество',
            slug='test-slug',
            description='test description'
        )
        cls.first_page_object_list = []
        cls.extra = 3
        for post_number in range(1, RECORDS_ON_THE_PAGE + cls.extra + 1):
            post = Post.objects.create(
                text=f'{post_number}. Заголовок тестовой записи',
                author=cls.user,
                group=cls.group
            )
            if post_number > cls.extra:
                cls.first_page_object_list.append(post)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.user)
        cache.clear()

    def test_first_page_containse_ten_records(self):
        """Первая страница содержит верное количество постов"""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context.get('page').object_list),
                         RECORDS_ON_THE_PAGE)

    def test_second_page_containse_three_records(self):
        """Вторая страница содержит верное количество постов"""
        response = self.authorized_client.get(
            reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context.get('page').object_list),
                         PaginatorViewsTest.extra)

    def test_first_page_show_correct_context(self):
        """Содержимое постов на первой странице соответствует ожиданиям"""
        response = self.authorized_client.get(reverse('posts:index'))
        # переворачиваем список постов, по порядку добавления
        page_objects = response.context.get('page').object_list[::-1]
        self.assertEqual(page_objects,
                         PaginatorViewsTest.first_page_object_list)


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

    def test_authorize_user_follow_and_unfollow_other_users(self):
        """
        Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок
        """
        # Считаем подписчиков до подписки
        followers_before = Follow.objects.filter(
            author=FollowTests.author).count()

        # Подписываем авторизованного пользователя на автора
        self.authorized_client.post(
            reverse('posts:profile_follow',
                    kwargs={'username': FollowTests.author}))

        # Считаем подписчиков после подписки
        followers_after = Follow.objects.filter(
            author=FollowTests.author).count()

        self.assertEqual(followers_before + 1, followers_after)

        # Удаляем подписку
        self.authorized_client.post(
            reverse('posts:profile_unfollow',
                    kwargs={'username': FollowTests.author}))

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
