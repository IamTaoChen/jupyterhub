import os
import sys
CONFIG_SCRIPT_DIR = os.getenv('CONFIG_SCRIPT_DIR', '/config')
sys.path.append(CONFIG_SCRIPT_DIR)
from MyConfig import MyConfig,my_pre_spawn_hook
from MyOAuth import MyOAuth
from MyDockerSpawner import MyDockerSpawner

import docker
c = get_config()

my_config=MyConfig(filename='/etc/jupyterhub/config.yaml')

# Generic
c.JupyterHub.admin_access = True
c.Spawner.default_url = '/lab'


# c.Application.log_level = 'DEBUG'
# c.JupyterHub.authenticator_class = GenericOAuthenticator
c.JupyterHub.authenticator_class = MyOAuth
c.MyOAuth.auto_login = True
c.MyOAuth.client_id = "xxxxxxx"
c.MyOAuth.client_secret = "xxxxxxx"
c.MyOAuth.token_url = "https://auth.xxxxxxx.com//accessToken"
c.MyOAuth.userdata_url = "https://auth.xxxxxxx.com/profile"
c.MyOAuth.authorize_url = "https://auth.xxxxxxx.com/oidc/authorize"
c.MyOAuth.oauth_callback_url = "https://code.xxxxxxx.com/hub/oauth_callback"
c.MyOAuth.logout_redirect_url = "https://auth.xxxxxxx.com/logout"
c.MyOAuth.username_key = "sub"
c.MyOAuth.login_service = 'OIDC'

c.MyOAuth.allowed_groups = ['Member']
# users with `administrator` role will be marked as admin
c.MyOAuth.admin_groups = ['Administrators', 'AdminJupyterHub']
c.MyOAuth.manage_groups = False
c.MyOAuth.scope = ['openid', 'profile', 'email']
c.MyOAuth.blocked_users = ['guest', 'test']
c.MyOAuth.admin_users = ['admin']
# Create system users just-in-time.
c.MyOAuth.create_system_users = True

c.JupyterHub.load_roles = my_config.load_roles()
c.JupyterHub.load_groups = my_config.load_groups()
c.JupyterHub.services = my_config.services()
c.JupyterHub.base_url = "/"
# SSL_DIR = '/ssl'
# c.JupyterHub.ssl_key = SSL_DIR+"/key.pem"
# c.JupyterHub.ssl_cert = SSL_DIR+"/fullchain.pem"

# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = "jupyterhub"
c.JupyterHub.hub_port = 8080

# Docker spawner
c.JupyterHub.spawner_class = 'MyDockerSpawner'
c.Spawner.pre_spawn_hook = my_pre_spawn_hook
ad_user = my_config.ad()
c.MyDockerSpawner.config_user(ad_user=ad_user)
# Other stuff
c.Spawner.cpu_limit = 30
c.Spawner.mem_limit = '64G'
# c.MyDockerSpawner.image = os.environ['DOCKER_JUPYTER_CONTAINER']
# c.MyDockerSpawner.allowed_images = my_config.allow_images()

# c.JupyterHub.cleanup_servers=False
c.MyDockerSpawner.network_name = "jupyterhub-net"
c.MyDockerSpawner.use_internal_ip = True
# c.DockerSpawner.working_dir = "/home/coder"
# See https://github.com/jupyterhub/dockerspawner/blob/master/examples/oauth/jupyterhub_config.py

# user data persistence
# see https://github.com/jupyterhub/dockerspawner#data-persistence-and-dockerspawner
notebook_dir = '/home/jovyan'
notebook_dir_public = notebook_dir+"/public"
# notebook_dir_data = notebook_dir+"/data"

user_dir = 'jupyterhub-{username}'
public_data = 'jupyterhub-public'

c.MyDockerSpawner.notebook_dir = notebook_dir
c.MyDockerSpawner.volumes = {
            user_dir: {'bind': notebook_dir, 'mode': 'rw'},
            public_data: {'bind': notebook_dir_public, 'mode': 'rw'},
            }
c.MyDockerSpawner.remove = True
c.MyDockerSpawner.debug = True
# c.DockerSpawner.host_ip = "0.0.0.0"
c.MyDockerSpawner.extra_host_config = {
    "device_requests": [
        docker.types.DeviceRequest(
            count=-1,
            capabilities=[["gpu"]],
        ),
    ],
}




# Persist hub data on volume mounted inside container
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"


# shutdown the server after no activity for an hour
c.ServerApp.shutdown_no_activity_timeout = 120 * 60
# shutdown kernels after no activity for 20 minutes
c.MappingKernelManager.cull_idle_timeout = 60 * 60
# check for idle kernels every two minutes
c.MappingKernelManager.cull_interval = 2 * 60


c.JupyterHub.allow_named_servers = True
c.JupyterHub.named_server_limit_per_user = 5
