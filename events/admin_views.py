from django.shortcuts import render


def hitcount_view(request, model_admin, object):
    model = model_admin.model
    return render(
        request,
        "admin/events/hitcount.html",
        {
            "original": object,
        },
    )
