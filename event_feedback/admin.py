from django.contrib import admin
from .models import (
    Survey,
    SurveyCategory,
    SurveyQuestion,
    SurveyResponse,
    QuestionAnswer,
)

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("event",)

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
