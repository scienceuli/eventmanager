import os

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase
from private_storage.fields import PrivateFileField


def _inside(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return os.path.commonpath([path, root]) == root


class PrivateStorageTest(SimpleTestCase):
    """Private files (invoices, confirmations, ...) must not be stored below
    MEDIA_ROOT: the web server serves MEDIA_ROOT directly under /media/,
    which bypasses django-private-storage's permission check. Without
    PRIVATE_STORAGE_ROOT, django-private-storage falls back to MEDIA_ROOT."""

    def test_private_storage_root_is_set(self):
        self.assertTrue(
            getattr(settings, "PRIVATE_STORAGE_ROOT", None),
            "PRIVATE_STORAGE_ROOT is not set, so private files land in MEDIA_ROOT",
        )

    def test_private_file_fields_are_stored_outside_media_root(self):
        fields = [
            (model, field)
            for model in apps.get_models()
            for field in model._meta.get_fields()
            if isinstance(field, PrivateFileField)
        ]
        self.assertTrue(fields)
        for model, field in fields:
            location = field.storage.location
            with self.subTest(field=f"{model._meta.label}.{field.name}", location=location):
                self.assertFalse(
                    _inside(location, settings.MEDIA_ROOT),
                    f"{location} is inside MEDIA_ROOT {settings.MEDIA_ROOT}",
                )
