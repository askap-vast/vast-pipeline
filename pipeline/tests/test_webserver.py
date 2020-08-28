from django.conf import settings as s
from django.test import Client
from django.test import SimpleTestCase, override_settings
from django.urls import reverse


@override_settings(
    BASE_URL='shbsfggiush',
    ROOT_URLCONF = 'pipeline.tests.urls'
)
class WebServerTest(SimpleTestCase):

    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_index_no_login(self):
        # Check nothing is running on /
        response = self.client.get('/')
        self.assertEqual(response.status_code, 404)

        # Check getting a redirect response on /shbsfggiush/
        # and the right re-direction
        response = self.client.get('/shbsfggiush/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/shbsfggiush/login/?next=/shbsfggiush/')
