from django.urls import reverse
from django.utils.safestring import mark_safe
from django.forms import widgets
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
