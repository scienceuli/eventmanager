from django.test import TestCase, RequestFactory
from django.shortcuts import reverse
from .views import IndexView, CategoryDetail, QuestionDetail
from . import models


class IndexViewTestCase(TestCase):
    def test_get_queryset_categories(self):
        """
        gets correct query set
        """
        request = RequestFactory().get(reverse("faqs:index-view"))
        view = IndexView()
        view.setup(request)

        category = models.Category.objects.create(
            name="category", description="this is a category"
        )
        models.Category.objects.create(
            name="category 2", description="this is a category"
        )
        models.Question.objects.create(question="category question", category=category)
        models.Question.objects.create(
            question="category question 2", category=category
        )
        models.Question.objects.create(question="question not in category")

        self.assertEqual(view.get_queryset().first(), models.Category.objects.first())
        self.assertNotEqual(
            view.get_queryset().first(), models.Question.objects.first()
        )
        self.assertNotEqual(view.get_queryset().first(), models.Category.objects.last())

    def test_get_context_object_name_categories(self):
        """
        gets correct context
        """
        request = RequestFactory().get(reverse("faqs:index-view"))
        view = IndexView()
        view.setup(request)

        self.assertEqual(view.get_context_object_name([]), "categories")
        self.assertNotEqual(view.get_context_object_name([]), "questions")


class CategoryDetailTestCase(TestCase):
    def setUp(self):
        models.Category.objects.create(name="cat1", description="descript")
        models.Category.objects.create(name="cat2", description="descript2")
        models.Category.objects.create(name="cat3", description="descript3")


class QuestionViewTestCase(TestCase):
    def setUp(self):
        category = models.Category.objects.create(name="cat1", description="descript")

        models.Question.objects.create(category=category, question="great question")
