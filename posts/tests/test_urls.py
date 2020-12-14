import datetime

from django.contrib.auth import get_user_model
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post, User


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.templates_url_names = [
            reverse('about-author'),
            reverse('about-spec'),
        ]
        cls.site = Site(
            pk=1,
            domain='127.0.0.1:8000',
            name='127.0.0.1:8000',
        )
        cls.site.save()

        FlatPage.objects.create(
            url=reverse('about-author'),
            title='about-author',
            content='its a about author content',
        ).sites.add(cls.site)
        FlatPage.objects.create(
            url=reverse('about-spec'),
            title='about-spec',
            content='its a about spec content',
        ).sites.add(cls.site)
        cls.static_urls = [
            '/',
            reverse('about-author'),
            reverse('about-spec')
        ]
        cls.guest_client = Client()
        # Создаем авторизованный клиент
        User = get_user_model()
        user = User.objects.create_user(username='Testuser')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(user)

    def test_static_pages_anonymous(self):
        """Статичные страницы доступны неавторизованному пользователю"""
        for url in StaticURLTests.static_urls:
            with self.subTest():
                response = StaticURLTests.guest_client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_static_pages_exists_at_desired_location(self):
        """Статичные страницы доступны авторизованному пользователю"""
        for url in StaticURLTests.static_urls:
            with self.subTest():
                response = StaticURLTests.authorized_client.get(url)
                self.assertEqual(response.status_code, 200)


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД для проверки доступности
        # адреса group/test-slug/
        cls.user = User.objects.create(
            username='testusername',
            email='testusername@testmail.com',
        )
        cls.user_not_author = User.objects.create(
            username='testnotauthor',
            email='testnotauthor@testmail.com',
        )
        cls.group = Group.objects.create(
            title='Тестовое сообщество',
            slug='test-slug',
            description='test description'
        )
        cls.post = Post.objects.create(
            text='Заголовок тестовой записи',
            pub_date=datetime.date.today(),
            author=cls.user,
            group=cls.group
        )
        cls.post_id = cls.post.id
        cls.templates_url_names = {
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
                                              'post_id': cls.post_id})
            ),
            'misc/404.html': '/404/',
            'misc/500.html': '/500/',
        }
        cls.urls_not_login_required = [
            reverse('posts:index'),
            reverse('posts:blogs', kwargs={'slug': 'test-slug'}),
            reverse('posts:profile', kwargs={'username': 'testusername'}),
            reverse('posts:post', kwargs={'username': 'testusername',
                                          'post_id': cls.post_id}),
        ]
        cls.post_id = cls.post.id
        cls.urls_error_pages = [
            '/404/',
            '/500/',
        ]

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)
        self.authorized_client_not_author = Client()
        self.authorized_client_not_author.force_login(
            PostURLTests.user_not_author)
        cache.clear()

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for template, reverse_name in PostURLTests.templates_url_names.items():
            with self.subTest():
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_new_redirect_anonymous_to_login(self):
        """Страница по адресу /new/ перенаправит анонимного
        пользователя на страницу логина.
        """
        url_new_post = reverse('posts:new_post')
        response = self.guest_client.get(url_new_post, follow=True)
        self.assertRedirects(
            response, reverse('login') + '?next=' + url_new_post)

    def test_post_edit_redirect_anonymous_to_login(self):
        """Страница по адресу /testusername/1/edit/ перенаправит анонимного
        пользователя на страницу логина.
        """
        url_post_edit = reverse('posts:post_edit',
                                kwargs={'username': PostURLTests.user,
                                        'post_id': PostURLTests.post_id})
        response = self.guest_client.get(url_post_edit, follow=True)
        self.assertRedirects(response,
                             reverse('login') + '?next=' + url_post_edit)

    def test_new_exists_at_desired_location(self):
        """Страница /new/ доступна авторизованному пользователю."""
        response = self.authorized_client.get(reverse('posts:new_post'),
                                              follow=True)
        self.assertEqual(response.status_code, 200)

    def test_post_edit_exists_at_desired_location(self):
        """Страница /testusername/1/edit/ доступна автору поста"""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'username': 'testusername',
                                               'post_id': PostURLTests.post_id}),
            follow=True)
        self.assertEqual(response.status_code, 200)

    def test_post_edit_redirect_auth_user_no_author(self):
        """Страница /testusername/1/edit/ переадресует авторизованного НЕавтора"""
        response = self.authorized_client_not_author.get(
            reverse('posts:post_edit', kwargs={'username': 'testusername',
                                               'post_id': PostURLTests.post_id}),
            follow=True)
        self.assertRedirects(response, reverse('posts:index'))

    def test_urls_not_login_required_exists_at_anonymous(self):
        """Общедоступные страницы доступны неавторизованному пользователю"""
        for reverse_name in PostURLTests.urls_not_login_required:
            with self.subTest():
                response = self.guest_client.get(reverse_name)
                self.assertEqual(response.status_code, 200)

    def test_urls_not_login_required_exists_at_desired_location(self):
        """Общедоступные страницы доступны авторизованному пользователю"""
        for reverse_name in PostURLTests.urls_not_login_required:
            with self.subTest():
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, 200)

    def test_urls_error_pages(self):
        """Страницы ошибок возвращают верный код"""
        for reverse_name in PostURLTests.urls_error_pages:
            with self.subTest():
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, int(reverse_name[1:-1]))
