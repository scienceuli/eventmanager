from django.urls import reverse
from django.utils.safestring import mark_safe
from django.forms import widgets, RadioSelect
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.conf import settings


class RelatedFieldWidgetCanAddWithModal(widgets.Select):
    def __init__(self, modal_id=None, label=None, *args, **kwargs):
        super(RelatedFieldWidgetCanAddWithModal, self).__init__(*args, **kwargs)

        # Be careful that here "reverse" is not allowed
        self.modal_id = modal_id
        self.label = label

    def render(self, name, value, *args, **kwargs):
        output = [
            super(RelatedFieldWidgetCanAddWithModal, self).render(
                name, value, *args, **kwargs
            )
        ]

        output.append(
            '<button id="%s" class="btn btn-primary" type="button" name="button">'
            % (self.modal_id)
        )

        output.append('<span class="fa fa-plus mr-2"></span>Neuen ')
        output.append("%s anlegen</button>" % (self.label))
        return mark_safe("".join(output))


class MyRadioSelect(RadioSelect):
    """überschreibt im Wesentlichen Django Radio Select widget"""

    def __init__(
        self, attrs=None, choices=(), ws_utilisations=None, tour_utilisations=None
    ):
        self.ws_utilisations = ws_utilisations
        self.tour_utilisations = tour_utilisations
        super(MyRadioSelect, self).__init__(attrs, choices=choices)
        # print("ws: ", self.ws_utilisations)

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        # print("called")
        option = super(MyRadioSelect, self).create_option(
            name, value, label, selected, index, subindex=None, attrs=None
        )
        # print("option:", option)
        # print("ws in create option", self.ws_utilisations)
        if not option.get("value"):
            option["attrs"]["disabled"] = "disabled"

        if option.get("value") == "I":
            option["attrs"]["disabled"] = True

        option["attrs"]["disabled"] = True

        if self.ws_utilisations[option.get("value")] <= 2:
            option["attrs"]["disabled"] = "disabled"

        return option
