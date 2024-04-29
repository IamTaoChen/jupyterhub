from __future__ import annotations
import os
from oauthenticator.generic import GenericOAuthenticator
from traitlets import Bool, Dict, Set, Unicode, Union, default
from jupyterhub.traitlets import Callable
import re
from tornado import gen
from urllib.parse import urlparse
import requests
from dataclasses import dataclass, field

import logging

# log = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)
# log.debug("groups: %s", "test")


class MyOAuth(GenericOAuthenticator):
    user_auth_state_key = 'oauth_user'
    group_path_in_userinfo = 'groups'

    discovery_url = Unicode(
            # default_value="",
            config=True,
            help="""
            Use this URL to get the discovery document for the OpenID Connect service.
            """,
        )
    
    @default("discovery_url")
    def _discovery_url_default(self):
        return os.environ.get("OAUTH2_DISCOVERY_URL", "")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not callable(self.claim_groups_key):
            #     # self.claim_groups_key = self.extract_group_from_dn
            self.claim_groups_key = self.get_user_groups
        self._oidc: OIDC_Endpoint = None


    @gen.coroutine
    def authenticate(self, handler, data=None):
        """
        This method is called when the user is authenticated.
        """
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


    def get_callback_url(self, handler=None)->str:
        """Get my OAuth redirect URL

        Either from config or guess based on the current request.
        """
        self._pre_auth()
        return super().get_callback_url(handler)
    
    def _pre_auth(self,_oidc:OIDC_Endpoint=None) -> None|OIDC_Endpoint:
        """
        This method is called before the authentication process starts.

        """
        if _oidc is None:
            _oidc=self._oidc
            if _oidc is None:
                _oidc = OIDC_Endpoint.from_discovery_url(self.discovery_url)
                self._oidc=_oidc                
        if _oidc is not None and _oidc.valid:
            self.token_url = _oidc.token_url or self.token_url
            self.userdata_url = _oidc.userinfo_url or self.userdata_url
            self.authorize_url = _oidc.authorize_url or self.authorize_url
            self.logout_redirect_url = _oidc.logout_redirect_url or self.logout_redirect_url
            
            # string_=str(_oidc)
            # log.debug("oidc: %s", string_)
            # log.debug("token_url: %s", self.token_url)
            # log.debug("userdata_url: %s", self.userdata_url)
            # log.debug("authorize_url: %s", self.authorize_url)
            # log.debug("logout_redirect_url: %s", self.logout_redirect_url)
            return _oidc
        else:
            return None
        


@dataclass
class OIDC_Endpoint:
    discovery_url: str
    token_url: str = field(default=None)
    userinfo_url: str = field(default=None)
    authorize_url: str = field(default=None)
    logout_redirect_url: str = field(default=None)

    def __post_init__(self):
        self.extract_endpoint()
    
    @property
    def valid(self) -> bool:
        return self._is_valid()

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
        return True
    
    def _is_valid(self) -> bool:
        return self.token_url is not None and self.userinfo_url is not None and self.authorize_url is not None and self.logout_redirect_url is not None

    @classmethod
    def from_discovery_url(cls, discovery_url: str) -> "OIDC_Endpoint" | None:
        """
        Create an instance of the class from the discovery URL.

        """
        data = cls.get_discovery_info2(discovery_url)
        if data is None:
            return None
        return cls(discovery_url=discovery_url)


    @classmethod
    def get_discovery_info(cls, discovery_url: str) -> dict|None:
        """
        Get the discovery information from the discovery URL.

        """
        if discovery_url is None or not isinstance(discovery_url, str) or len(discovery_url) == 0:
            return None
        response = requests.get(discovery_url)
        # check if the request is successful
        if response.status_code == 200:
            # analyze the JSON response
            data = response.json()
            if "issuer" in data and isinstance(data['issuer'], str):
                return data
            return None
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
            discovery_url_list.append(f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}{suffix}")
        for url in discovery_url_list:
            data = cls.get_discovery_info(url)
            if data is not None:
                return data
        return None


if __name__ == "__main__":
    discovery_url = "https://auth.eqe-lab.com/realms/eqe"
    MyOAuth.discovery_url = discovery_url
    auth = MyOAuth()
    auth._pre_auth()

    # response = requests.get(url)
    # if response.status_code == 200:
    #     break
