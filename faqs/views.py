from django.core.exceptions import PermissionDenied
from django.shortcuts import reverse
from django.views import generic
from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings
from . import models


class IndexView(generic.ListView):
    """
    this view depending on settings either displays all the categories as a list if the categories is enabled using the categories_list.html template

    if categories are not enabled it will then show a list of all the questions using questions_list.html template
    """

    def get_template_names(self):
        return "faqs/categories_list.html"

    def get_queryset(self):
        return models.Category.objects.all()

    def get_context_object_name(self, object_list):
        return "categories"


class CategoryDetail(generic.DetailView):
    """
    this view only runs when categories are enabled
    this view shows all the questions related to this category
    """

    model = models.Category
    template_name = "faqs/category_detail.html"


class QuestionDetail(generic.DetailView):
    model = models.Question
    template_name = "faqs/question_detail.html"
    context_object_name = "question"

    def get_object(self, queryset=None):
        return self.model.objects.get(
            category__slug=self.kwargs["slug"], slug=self.kwargs["question"]
        )
