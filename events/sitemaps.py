from events.models import Event

from django.contrib.sitemaps import Sitemap


class EventSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.5

    def items(self):
        return Event.objects.filter(pub_status="PUB")

    def lastmod(self, obj):

        return obj.date_modified
