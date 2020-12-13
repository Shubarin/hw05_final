import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import get_object_or_404
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post, User


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='testusername',
            email='testusername@testmail.com',
        )
        cls.group = Group.objects.create(
            title='Тестовое сообщество',
            slug='test-slug',
            description='test description'
        )
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=tempfile.gettempdir())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()

        form_data = {
            'text': 'Заголовок тестовой записи',
            'author': PostFormTests.user,
            'group': PostFormTests.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:new_post'),
            data=form_data,
            follow=True
        )
        # Получаем данные формы из ответа страницы
        response_form_data = response.context['page'].object_list[0]
        form_text = response_form_data.text
        form_author = response_form_data.author
        form_group = response_form_data.group.id
        # Получаем последнюю запись из БД
        post = Post.objects.latest('id')

        self.assertEqual(form_text, post.text)
        self.assertEqual(form_author, post.author)
        self.assertEqual(form_group, post.group.id)
        self.assertRedirects(response, reverse('posts:index'))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, 200)

    def test_edit_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        old_post = Post.objects.create(
            text='Заголовок тестовой записи',
            author=PostFormTests.user,
            group=PostFormTests.group
        )
        form_data = {
            'text': 'Новый заголовок тестовой записи',
            'author': PostFormTests.user,
            'group': PostFormTests.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={
                'username': PostFormTests.user,
                'post_id': old_post.id
            }),
            data=form_data,
            follow=True
        )
        # обновляем значения старой записи
        old_post.refresh_from_db()
        # Получаем последнюю запись из БД
        new_post = get_object_or_404(Post.objects, id=old_post.id)

        self.assertEqual(new_post.text, old_post.text)
        self.assertEqual(old_post.author, new_post.author)
        self.assertEqual(old_post.group.id, new_post.group.id)
        self.assertRedirects(response, reverse('posts:post', kwargs={
            'username': PostFormTests.user.username,
            'post_id': new_post.id}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, 200)

    def test_new_post_creates_post_with_image(self):
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Trying out some images.',
            'group': PostFormTests.group.id,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:new_post'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
