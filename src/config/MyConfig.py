'''
Descripttion: 
version: 
Author: Tao Chen
Date: 2023-06-18 07:24:43
LastEditors: Tao Chen
LastEditTime: 2023-06-18 07:36:08
'''
#!/bin/python3
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from AdUsers import *
from typing import Any
import yaml
import os
import sys
current_folder = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_folder)
# -----

# log = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)
# log.debug("groups: %s", groups)


@dataclass
class AiConfig:
    enable: bool
    name: str
    key: str


@dataclass
class UserUpdate:
    # If enabled is false, the uid and gid and username will be fetched from the container
    enable: bool = False
    # If from_ad is true, the uid and gid will be fetched from AD
    # If from_ad is false, the uid and gid will be fetched 1000:1000
    from_ad: bool = False
    defualt_gid: int = 1000
    defualt_uid: int = 1000
    default_group: str = 'users'


@dataclass
class ImageConfig:
    name: str = None
    image: str = None
    allow_collab: bool = True

    def from_dict(self, name: str, data: dict[str, str] | str):
        """
        return ImageConfig from dict
        """
        self.name = name
        if isinstance(data, str):
            self.image = data
        elif isinstance(data, dict):
            if 'image' in data:
                self.image = data['image']
            else:
                raise Exception("image not found in image config")
            if 'allow_collab' in data:
                self.allow_collab = data['allow_collab']
        else:
            raise Exception("image config is not dict or str")


@dataclass
class ImageConfigMulti:
    data: dict[str, ImageConfig] = field(default_factory=dict)

    def from_dict(self, data: dict[str, dict[str, str]]):
        """
        return ImageConfigMulti from dict
        """
        self.data = {}
        names = data.keys()
        for name in names:
            image_config = ImageConfig()
            image_config.from_dict(name, data[name])
            self.data[name] = image_config

    def if_allow_collab_by_name(self, name: str) -> bool:
        """
        chech the designated image if allow collab
        """
        if name not in self.data:
            return False
        return self.data[name].allow_collab

    def if_allow_collab_by_image(self, image: str) -> bool:
        """
        chech the designated image if allow collab
        """
        for name in self.data:
            if self.data[name].image == image:
                return self.data[name].allow_collab
        return False

    def allowed_images(self) -> dict[str, str]:
        """
        return allowed images
        """
        images = {}
        for name in self.data:
            images[name] = self.data[name].image
        return images


class MyConfig:
    def __init__(self, filename: str = '/etc/jupyterhub/config.yaml'):
        self.filename = filename
        self.config: dict[str, Any] = {}
        self.load()

    def load(self, filename: str = None):
        if filename is None:
            filename = self.filename
        with open(filename) as f:
            self.config = yaml.safe_load(f)

    def allowed_images(self) -> dict[str, str]:
        """
        return allowed images
        """
        images_config = self._read_image_config()
        return images_config.allowed_images()

    def load_groups(self) -> dict[dict[str, list[str]]]:
        if 'groups' not in self.config:
            return {}
        return self.config['groups']

    def load_roles(self) -> list[dict[str, dict[str, list[str]]], dict[str, list[str]]]:
        """
        load roles from config file
        """
        if 'roles' not in self.config:
            return []
        return self.config['roles']

    def services(self) -> list[dict]:
        if 'services' not in self.config:
            return []
        return self.config['services']

    def _read_image_config(self) -> ImageConfigMulti:
        if 'allowed_images' not in self.config:
            return ImageConfigMulti()
        images_config = ImageConfigMulti()
        images_config.from_dict(self.config['allowed_images'])
        return images_config

    def user_source(self) -> UserUpdate:
        if 'user_update' not in self.config:
            return UserUpdate()
        user = self.config['user_update']
        return UserUpdate(enable=user['enable'],
                          from_ad=user['from_ad'],
                          defualt_uid=user['defualt_uid'],
                          defualt_gid=user['defualt_gid'],
                          default_group=user['default_group']
                          )

    @classmethod
    def pre_spawn_hook_collab(cls, spawner):
        """
        execute before spawn for collab
        """
        group_names = {group.name for group in spawner.user.groups}
        collab_enable_args = ['--LabApp.collaborative=True']
        collab_disable_args = ['--LabApp.collaborative=False', '--YDocExtension.disable_rtc=True']
        # '--YDocExtension.disable_rtc=False'
        if "collaborative" in group_names:
            spawner.log.info(f"Enabling RTC for user {spawner.user.name}")
            cls.spawner_args_append_if_not_exist(spawner, collab_enable_args)
        else:
            spawner.log.info(f"Disabling RTC for user {spawner.user.name}")
            cls.spawner_args_append_if_not_exist(spawner, collab_disable_args)

    def ad(self) -> AdUser:
        if 'ad' not in self.config or self.config['ad']['enable'] is not True:
            return None
        ad = self.config['ad']
        ad_config = ad['config']
        ldap_config = LdapConfig()
        ldap_config.HOST = ad_config['host']
        ldap_config.PORT = ad_config['port']
        ldap_config.BASE_DN = ad_config['base_dn']
        ldap_config.BIND_DN = ad_config['bind_dn']
        ldap_config.BIND_PW = ad_config['bind_pw']
        ldap_config.USER_BASE_RDN = ad_config['user_search_rdn']
        ldap_config.GROUP_BASE_RDN = ad_config['group_search_rdn']
        ldap_config.USER_FILTER = ad_config['user_search_filter']
        ldap_config.USERNAME_ATTRIBUTE = ad_config['user_username_attribute']
        if 'local_cache' not in ad or ad['local_cache']['enable'] is not True:
            connect = '/tmp/ad_cache.sqlite3'
            table = 'ad_cache'
        else:
            connect = ad['local_cache']['connect']
            table = ad['local_cache']['table']
        user_sql = UserSql(connect)
        # log.debug("connect",connect)
        user_sql.table = table
        ad_user = AdUser(ldap_config, user_sql)
        if 'force_gid' in ad_config and ad_config['force_gid']['enable'] is True:
            ad_user.force_gid = ad_config['force_gid']['gid']
            ad_user.force_gname = ad_config['force_gid']['name']
        if 'append_groups' in ad:
            ad_user.append_groups = ad['append_groups']
        if 'allow_users' in ad:
            ad_user.allow_users = ad['allow_users']
        return ad_user

    def ai(self) -> AiConfig:
        settting_name = 'ai'
        if settting_name not in self.config or self.config[settting_name]['enable'] is not True:
            return None
        ai_config = self.config[settting_name]
        ai_config = AiConfig(ai_config['enable'], ai_config['name'], ai_config['key'])
        return ai_config

    @classmethod
    def spawner_args_append_if_not_exist(cls, spawner, args):
        if args is None:
            return
        elif isinstance(args, str):
            args = [args]
        elif not isinstance(args, list):
            return
        for arg in args:
            arg = arg.strip()
            if arg not in spawner.args:
                spawner.args.append(arg)


def get_userinfo(spawner, ad_user: AdUser = None, user_source: UserUpdate = None) -> tuple[bool, UserInfo] | None:
    """
    Get user information from AD or local(1000,1000). If user_source is None, the user information will be fetched from the container

    Returns:
        bool: if the user information is from AD
        UserInfo: user information
    if user is not allowed, return None
    """
    if user_source is None:
        from_ad = True
    elif user_source.enable is False:
        from_ad = False
    else:
        from_ad = user_source.from_ad
    username = spawner.user.name
    if ad_user is not None:
        allow_users = ad_user.allow_users
        if allow_users is not None and username not in allow_users:
            return None
    if from_ad:
        try:
            userinfo = ad_user.user_check(username)
            return True, userinfo
        except Exception as e:
            spawner.log.error(f"User {username} not found in AD")
            spawner.notebook_dir = '/home/jovyan'
            spawner.log.error(e)
            return None
    else:
        userinfo = UserInfo()
        userinfo.uid = user_source.defualt_uid
        userinfo.gid = user_source.defualt_gid
        userinfo.username = username
        userinfo.groupname = user_source.default_group
    return False, userinfo


def config_user(spawner, ad_user: AdUser = None, user_source: UserUpdate = None, append_groups: list[str] = None):
    """
    Config user's uid, gid and home directory from AD informatin. this is because we mount the user's home directory to the host
    """
    from_ad, userinfo = get_userinfo(spawner, ad_user, user_source)
    if userinfo is None:
        return
    spawner.extra_create_kwargs.update({'user': 'root'})
    spawner.extra_create_kwargs.update({'working_dir': '/home/'+userinfo.username})
    spawner.environment['CHOWN_HOME'] = 'no'
    spawner.environment['CHOWN_HOME_OPTS'] = ''
    spawner.environment['NB_UID'] = userinfo.uid
    spawner.environment['NB_GID'] = userinfo.gid
    spawner.environment['NB_USER'] = userinfo.username
    spawner.environment['NB_GROUP'] = userinfo.groupname
    if from_ad:
        spawner.environment["GIT_AUTHOR_NAME"] = userinfo.cn
        spawner.environment["GIT_COMMITTER_NAME"] = userinfo.cn
        spawner.environment["GIT_AUTHOR_EMAIL"] = userinfo.mail
        spawner.environment["GIT_COMMITTER_EMAIL"] = userinfo.mail
    return


def config_ai(spawner, ai_config: AiConfig = None):
    if ai_config is None:
        return
    spawner.environment[ai_config.name] = ai_config.key


def my_pre_spawn_hook(spawner):
    CONFIG_FILE = os.getenv('CONFIG_FILE', '/etc/jupyterhub/config.yaml')
    my_config = MyConfig(filename=CONFIG_FILE)
    ad_user = my_config.ad()
    user_source = my_config.user_source()
    config_user(spawner=spawner, ad_user=ad_user, user_source=user_source)
    config_ai(spawner, my_config.ai())
    image_name = spawner.image
    image_config = my_config._read_image_config()
    if image_config.if_allow_collab_by_image(image_name):
        MyConfig.pre_spawn_hook_collab(spawner)


if __name__ == "__main__":
    config = MyConfig(filename='./config.yaml')
