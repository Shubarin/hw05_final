import datetime

from django.test import TestCase
from posts.models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='testusername',
            email='testusername@testmail.com',
        )
        cls.group = Group.objects.create(
            title='Тестовое сообщество',
            slug='testslug',
            description='test description'
        )
        cls.post = Post.objects.create(
            text='Заголовок тестовой записи',
            pub_date=datetime.date.today(),
            author=cls.user,
            group=cls.group
        )

    def test_verbose_name(self):
        """verbose_name полей text, group совпадает с ожидаемым."""
        post = PostModelTest.post
        field_verboses = {
            'text': 'Текст сообщения',
            'group': 'Сообщество',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                self.assertEqual(
                    post._meta.get_field(value).verbose_name, expected)

    def test_help_text(self):
        """help_text полей text, group совпадает с ожидаемым."""
        post = PostModelTest.post
        field_help_texts = {
            'text': 'Напишите текст вашего сообщения',
            'group': 'Выберите название сообщества',
        }
        for value, expected in field_help_texts.items():
            with self.subTest(value=value):
                self.assertEqual(
                    post._meta.get_field(value).help_text, expected)

    def test_object_name_is_text_field(self):
        """__str__  post - это строчка с содержимым post.text."""
        post = PostModelTest.post
        expected_object_name = post.text[:15]
        self.assertEquals(expected_object_name, str(post))

    def test_object_name_is_group_field(self):
        """__str__  group - это строчка с содержимым group.text."""
        group = PostModelTest.group
        expected_object_name = group.title
        self.assertEquals(expected_object_name, str(group))
