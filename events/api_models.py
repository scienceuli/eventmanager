from django.db import models


class VfllMemberEmail(models.Model):
    email = models.EmailField(max_length=254)

    def __str__(self):
        return self.email
