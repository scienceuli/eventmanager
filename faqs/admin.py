from django.contrib import admin
from .models import *
from django.conf import settings


class AnswerAdmin(admin.ModelAdmin):
    list_display = (
        "answer",
        "question",
    )
    search_fields = ["answer", "question"]
    readonly_fields = ("slug",)


class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name", "description"]
    readonly_fields = ("slug",)

    list_display = ["name", "slug", "description"]


class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "category",
        "slug",
    )
    list_filter = ["category"]
    search_fields = ["question"]
    readonly_fields = ("slug",)


admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)

admin.site.register(Category, CategoryAdmin)
