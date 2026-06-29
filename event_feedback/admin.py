import json
from pathlib import Path

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path

from .models import (
    Survey,
    SurveyCategory,
    SurveyQuestion,
    SurveyResponse,
    QuestionAnswer,
)

TEMPLATE_PATH = Path(__file__).parent / "survey_templates" / "default.json"


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("event",)
    change_list_template = "admin/event_feedback/survey/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "template-editor/",
                self.admin_site.admin_view(self.template_editor_view),
                name="event_feedback_survey_template_editor",
            ),
        ]
        return custom + urls

    def template_editor_view(self, request):
        error = None
        if request.method == "POST":
            content = request.POST.get("content", "")
            try:
                json.loads(content)
                TEMPLATE_PATH.write_text(content, encoding="utf-8")
                self.message_user(request, "Feedback-Vorlage gespeichert.")
                return redirect("..")
            except json.JSONDecodeError as e:
                error = f"Ungültiges JSON: {e}"
        else:
            content = TEMPLATE_PATH.read_text(encoding="utf-8")

        context = {
            **self.admin_site.each_context(request),
            "title": "Feedback-Vorlage bearbeiten",
            "content": content,
            "error": error,
            "opts": self.model._meta,
        }
        return render(request, "admin/event_feedback/survey/template_editor.html", context)

class SurveyQuestionInline(admin.TabularInline):
    model = SurveyQuestion
    extra = 1

class SurveyCategoryInline(admin.StackedInline):
    model = SurveyCategory
    extra = 1

@admin.register(SurveyCategory)
class SurveyCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "survey", "order")
    inlines = [SurveyQuestionInline]


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "category", "order")
    list_filter = ("category",)

class QuestionAnswerInline(admin.TabularInline):
    model = QuestionAnswer
    extra = 0
    readonly_fields = ("question", "rating", "comment")
    can_delete = False

@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ("survey", "consent", "created_at")
    inlines = [QuestionAnswerInline]

    readonly_fields = ("survey", "consent", "final_comment")

    def has_add_permission(self, request):
        return False
