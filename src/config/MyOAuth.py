from __future__ import annotations
from oauthenticator.generic import GenericOAuthenticator
import re
from tornado import gen
from urllib.parse import urlparse
import requests
from dataclasses import dataclass, field

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
        self._oidc: OIDC_Endpoint = None
        try:
            self.discovery_url: str = kwargs.get("discovery_url")
        except KeyError:
            self.discovery_url: str = None

    @gen.coroutine
    def authenticate(self, handler, data=None):
        """
        This method is called when the user is authenticated.
        """
        # Call the parent class method first
        self._pre_auth()
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

    def get_allowed_groups(self, groups: list[str]) -> list[str]:
        """
        Check if the user is in the allowed groups.
        """
        allowed_groups = set(self.allowed_groups)
        groups = set(groups)
        groups_filter = allowed_groups.intersection(groups)
        return list(groups_filter)

    @classmethod
    def get_user_groups(cls, user_info: dict[str, str]) -> list[str]:
        """
        Extract the groups from the user information.

        This is written for keycloak. The format of the groups is like this: /group1/subgroup, /group2, /group3.

        If you don't use keycloak, you may need to override this method or set the claim_groups_key attribute(callable) to a function that extracts the groups from the user information.
        """
        group_path_in_userinfo = cls.group_path_in_userinfo or 'groups'
        groups = user_info.get(group_path_in_userinfo, [])
        groups = [group[1:] if group.startswith('/') else group for group in groups]
        return set(groups)

    @classmethod
    def extract_group_from_dn(self, user_info: dict[str, str]):
        """
        Extract the groups from the user information.
        """
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

    def _pre_auth(self) -> None:
        """
        This method is called before the authentication process starts.

        """
        if self._oidc is None:
            self._oidc = OIDC_Endpoint.from_discovery_url(self.discovery_url)
        if self._oidc is not None and self._oidc.valid:
            self.token_url = self.token_url or self._oidc.token_url
            self.userdata_url = self.userdata_url or self._oidc.userinfo_url
            self.authorize_url = self.authorize_url or self._oidc.authorize_url
            self.logout_redirect_url = self.logout_redirect_url or self._oidc.logout_redirect_url


@dataclass
class OIDC_Endpoint:
    discovery_url: str
    token_url: str = field(default=None)
    userinfo_url: str = field(default=None)
    authorize_url: str = field(default=None)
    logout_redirect_url: str = field(default=None)
    valid: bool = field(default=False)

    def __post_init__(self):
        self.extract_endpoint()

    def extract_endpoint(self, discovery_url: str = None) -> bool:
        """
        Extract the endpoint from the discovery URL. 

        If the discovery URL is None, try to use the discovery URL from the class attribute. And if the discovery URL is None, return None.

        Return True if the extraction is successful, otherwise return False.

        """
        if discovery_url is None:
            discovery_url = self.discovery_url
        if discovery_url is None:
            return False
        data = self.get_discovery_info2(discovery_url)
        if data is None:
            return False
        self.token_url = data.get("token_endpoint")
        self.userinfo_url = data.get("userinfo_endpoint")
        self.authorize_url = data.get("authorization_endpoint")
        self.logout_redirect_url = data.get("end_session_endpoint")
        self.valid = True
        return True

    @classmethod
    def from_discovery_url(cls, discovery_url: str) -> "OIDC_Endpoint" | None:
        """
        Create an instance of the class from the discovery URL.

        """
        data = cls.get_discovery_info2(discovery_url)
        if data is None:
            return None
        return cls(discovery_url=discovery_url,
                   token_url=data.get("token_endpoint"),
                   userinfo_url=data.get("userinfo_endpoint"),
                   authorize_url=data.get("authorization_endpoint"),
                   logout_redirect_url=data.get("end_session_endpoint"),
                   valid=True
                   )

    @classmethod
    def get_discovery_info(cls, discovery_url: str) -> dict:
        """
        Get the discovery information from the discovery URL.

        """
        response = requests.get(discovery_url)
        # check if the request is successful
        if response.status_code == 200:
            # analyze the JSON response
            data = response.json()
            return data
        else:
            print("Failed to retrieve data: Status code", response.status_code)
            return None

    @classmethod
    def get_discovery_info2(cls, discovery_url: str) -> dict:
        """
        Try to parse the discovery URL and get the discovery information from the URL.
        """
        suffix = "/.well-known/openid-configuration"
        parsed_url = urlparse(discovery_url)
        discovery_url_list = [discovery_url]
        if parsed_url.path.endswith(suffix):
            pass
        else:
            discovery_url_list.append(f"{parsed_url.scheme}://{parsed_url.netloc}{suffix}")
        for url in discovery_url_list:
            data = cls.get_discovery_info(url)
            if data is not None:
                return data
        return None


if __name__ == "__main__":
    discovery_url = "https://auth.eqe-lab.com/realms/eqe/.well-known/openid-configuration"
    suffix = "/.well-known/openid-configuration"
    parsed_url = urlparse(discovery_url)
    discovery_url_list = [discovery_url]
    if parsed_url.path.endswith(suffix):
        pass
    else:
        discovery_url_list.append(f"{parsed_url.scheme}://{parsed_url.netloc}{suffix}")
    for url in discovery_url_list:
        print(url)
        data = OIDC_Endpoint.get_discovery_info(url)
        if data is not None:
            break
    print(data)
    # response = requests.get(url)
    # if response.status_code == 200:
    #     break
