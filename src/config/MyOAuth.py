
from oauthenticator.generic import GenericOAuthenticator
import re
from tornado import gen
# import logging

# log = logging.getLogger(__name__)  
# logging.basicConfig(level=logging.DEBUG) 
# log.debug("groups: %s", groups)
class MyOAuth(GenericOAuthenticator):
    user_auth_state_key = 'oauth_user'
    group_path_in_userinfo = 'groups'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not callable(self.claim_groups_key):
        #     # self.claim_groups_key = self.extract_group_from_dn
            self.claim_groups_key = self.get_user_groups

    @gen.coroutine
    def authenticate(self, handler, data=None):
        # Call the parent class method first
        auth_model = yield super().authenticate(handler, data)
        self.manage_groups = True
        if self.manage_groups:
            user_info = auth_model["auth_state"][self.user_auth_state_key]
            # Get user groups
            if callable(self.claim_groups_key):
                groups = self.claim_groups_key(user_info)
            else:
                groups = user_info.get(self.claim_groups_key)
            auth_model['groups'] = self.get_allowed_groups(groups)
        return auth_model

    def get_allowed_groups(self, groups):
        allowed_groups = set(self.allowed_groups)
        groups = set(groups)
        groups_filter = allowed_groups.intersection(groups)
        return list(groups_filter)


    @classmethod
    def get_user_groups(cls, user_info):
        groups = user_info.get('groups', [])
        groups = [group[1:] if group.startswith('/') else group for group in groups]
        return set(groups)

    @classmethod
    def extract_group_from_dn(self, user_info):
        # dns = user_info.get('zoneinfo')
        dns = user_info.get(self.group_path_in_userinfo)
        if not isinstance(dns, list):
            return []
        groups = []
        for dn in dns:
            # match = re.match(r'cn=([^,]+)', dn)
            match = re.match(r'cn=([^,]+),\s?ou=([^,]+)', dn)
            if match:
                groups.append(match.group(1))
        return groups

    def extract_endpoint(self, discovery_url)->None:
        """
        Extract the endpoint from the discovery URL. If the discovery URL is None, return None.
        """
        if discovery_url is None:
            return None
        # If the discovery URL is not None, extract the endpoint from the URL.
        # Try to match the discovery URL with the regular expression.
        REGEX = r'^(https?://[^/]+)'
        match = re.match(REGEX, discovery_url)
        if  not match:
            return None
        