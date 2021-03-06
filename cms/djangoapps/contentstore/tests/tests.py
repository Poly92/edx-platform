from django.test.client import Client
from django.core.urlresolvers import reverse

from .utils import parse_json, user, registration
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase


class ContentStoreTestCase(ModuleStoreTestCase):
    def _login(self, email, pw):
        """Login.  View should always return 200.  The success/fail is in the
        returned json"""
        resp = self.client.post(reverse('login_post'),
                                {'email': email, 'password': pw})
        self.assertEqual(resp.status_code, 200)
        return resp

    def login(self, email, pw):
        """Login, check that it worked."""
        resp = self._login(email, pw)
        data = parse_json(resp)
        self.assertTrue(data['success'])
        return resp

    def _create_account(self, username, email, pw):
        """Try to create an account.  No error checking"""
        resp = self.client.post('/create_account', {
            'username': username,
            'email': email,
            'password': pw,
            'location': 'home',
            'language': 'Franglish',
            'name': 'Fred Weasley',
            'terms_of_service': 'true',
            'honor_code': 'true',
        })
        return resp

    def create_account(self, username, email, pw):
        """Create the account and check that it worked"""
        resp = self._create_account(username, email, pw)
        self.assertEqual(resp.status_code, 200)
        data = parse_json(resp)
        self.assertEqual(data['success'], True)

        # Check both that the user is created, and inactive
        self.assertFalse(user(email).is_active)

        return resp

    def _activate_user(self, email):
        """Look up the activation key for the user, then hit the activate view.
        No error checking"""
        activation_key = registration(email).activation_key

        # and now we try to activate
        resp = self.client.get(reverse('activate', kwargs={'key': activation_key}))
        return resp

    def activate_user(self, email):
        resp = self._activate_user(email)
        self.assertEqual(resp.status_code, 200)
        # Now make sure that the user is now actually activated
        self.assertTrue(user(email).is_active)


class AuthTestCase(ContentStoreTestCase):
    """Check that various permissions-related things work"""

    def setUp(self):
        self.email = 'a@b.com'
        self.pw = 'xyz'
        self.username = 'testuser'
        self.client = Client()

    def check_page_get(self, url, expected):
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, expected)
        return resp

    def test_public_pages_load(self):
        """Make sure pages that don't require login load without error."""
        pages = (
            reverse('login'),
            reverse('signup'),
        )
        for page in pages:
            print "Checking '{0}'".format(page)
            self.check_page_get(page, 200)

    def test_create_account_errors(self):
        # No post data -- should fail
        resp = self.client.post('/create_account', {})
        self.assertEqual(resp.status_code, 200)
        data = parse_json(resp)
        self.assertEqual(data['success'], False)

    def test_create_account(self):
        self.create_account(self.username, self.email, self.pw)
        self.activate_user(self.email)

    def test_login(self):
        self.create_account(self.username, self.email, self.pw)

        # Not activated yet.  Login should fail.
        resp = self._login(self.email, self.pw)
        data = parse_json(resp)
        self.assertFalse(data['success'])

        self.activate_user(self.email)

        # Now login should work
        self.login(self.email, self.pw)

    def test_private_pages_auth(self):
        """Make sure pages that do require login work."""
        auth_pages = (
            reverse('index'),
        )

        # These are pages that should just load when the user is logged in
        # (no data needed)
        simple_auth_pages = (
            reverse('index'),
        )

        # need an activated user
        self.test_create_account()

        # Create a new session
        self.client = Client()

        # Not logged in.  Should redirect to login.
        print 'Not logged in'
        for page in auth_pages:
            print "Checking '{0}'".format(page)
            self.check_page_get(page, expected=302)

        # Logged in should work.
        self.login(self.email, self.pw)

        print 'Logged in'
        for page in simple_auth_pages:
            print "Checking '{0}'".format(page)
            self.check_page_get(page, expected=200)

    def test_index_auth(self):

        # not logged in.  Should return a redirect.
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 302)

        # Logged in should work.
