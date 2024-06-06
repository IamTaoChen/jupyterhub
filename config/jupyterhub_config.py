import os
import sys

# The following is necessary
#  ==============================================================================
CONFIG_SCRIPT_DIR = os.getenv('CONFIG_SCRIPT_DIR', '/config')
CONFIG_FILE = os.getenv('CONFIG_FILE', '/etc/jupyterhub/config.yaml')
sys.path.append(CONFIG_SCRIPT_DIR)
from MyConfig import MyConfig,my_pre_spawn_hook
from MyOAuth import MyOAuth
from MyDockerSpawner import MyDockerSpawner
import docker
# ==============================================================================
c = get_config()

my_config=MyConfig(filename=CONFIG_FILE)

# Generic
# c.Application.log_level = 'DEBUG'
c.JupyterHub.admin_access = True
c.Spawner.default_url = '/lab'

# Authenticator
c.JupyterHub.authenticator_class = MyOAuth
c.MyOAuth.auto_login = True
c.MyOAuth.discovery_url = "https://auth.example.com/realms/realm"+"/.well-known/openid-configuration"
# or (you can add "/.well-known/openid-configuration" or not)
c.MyOAuth.discovery_url = "https://auth.example.com/realms/realm"
c.MyOAuth.client_id = "code-oidc"
c.MyOAuth.client_secret = "CHANGEIT"
c.MyOAuth.scope = ['openid', 'profile', 'email', 'groups']
c.MyOAuth.oauth_callback_url = "https://code.example.com/hub/oauth_callback"
c.MyOAuth.username_claim = "preferred_username"
c.MyOAuth.login_service = 'Example'
# If group is not defined, all users will be allowed
GROUP = ['group1', 'group2', 'admins']
c.MyOAuth.allowed_groups = GROUP
# users with `administrator` role will be marked as admin
c.MyOAuth.admin_groups = ['Administrators', 'AdminJupyterHub','admins']
c.MyOAuth.manage_groups = False
c.MyOAuth.blocked_users = ['guest', 'test']
c.MyOAuth.admin_users = ['admins']
# Create system users just-in-time.
# c.MyOAuth.create_system_users = True

# Load roles, groups and services
c.JupyterHub.load_roles = my_config.load_roles()
c.JupyterHub.load_groups = my_config.load_groups()
c.JupyterHub.services = my_config.services()

c.Spawner.pre_spawn_hook = my_pre_spawn_hook

c.JupyterHub.base_url = "/"

# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = "jupyterhub"
c.JupyterHub.hub_port = 8080

# Docker spawner
c.JupyterHub.spawner_class = MyDockerSpawner


# The allowed images are defined in config.yaml
c.MyDockerSpawner.allowed_images = my_config.allowed_images()

# c.JupyterHub.cleanup_servers=False
c.MyDockerSpawner.network_name = "jupyterhub"
c.MyDockerSpawner.use_internal_ip = True


# The volume mounted inside the container
# Persist hub data on volume mounted inside container
notebook_dir_public = "/public"
notebook_dir_lab_data = "/lab"

lab_data = '/lab'
public_data = '/public'
local_home = '/home/users/{username}'
jupyter_home = '/home/{username}'
c.MyDockerSpawner.notebook_dir = jupyter_home
c.MyDockerSpawner.volumes = {
            public_data: {'bind': notebook_dir_public, 'mode': 'rw'},
            lab_data: {'bind': notebook_dir_lab_data, 'mode': 'ro'},
            local_home: {'bind': jupyter_home, 'mode': 'rw'}
            }

# Others
c.MyDockerSpawner.remove = True
c.MyDockerSpawner.debug = False
c.MyDockerSpawner.host_ip = "0.0.0.0"
# Extra kwargs for docker
c.MyDockerSpawner.extra_create_kwargs = {
    # Define the hostname of the container
    'hostname': '{username}-{servername}'
}


# Resource Users can use
c.MyDockerSpawner.cpu_limit = 32.0
c.MyDockerSpawner.mem_limit = '16G'
# # if you want to use GPU, uncomment the following lines
# c.MyDockerSpawner.extra_host_config = {
#     "device_requests": [
#         docker.types.DeviceRequest(
#             count=-1,
#             capabilities=[["gpu"]],
#         ),
#     ],
# }



# c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"

# shutdown the server after no activity for an hour
c.ServerApp.shutdown_no_activity_timeout = 120 * 60
# shutdown kernels after no activity for 20 minutes
c.MappingKernelManager.cull_idle_timeout = 60 * 60
# check for idle kernels every two minutes
c.MappingKernelManager.cull_interval = 2 * 60


c.JupyterHub.allow_named_servers = True
c.JupyterHub.named_server_limit_per_user = 10


c.ConfigurableHTTPProxy.debug = False
