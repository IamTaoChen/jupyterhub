from __future__ import annotations
from dockerspawner import DockerSpawner
from dataclasses import dataclass, field


@dataclass
class Profile:
    """Dataclass for storing details of each profile."""
    name: str = 'minimal-notebook'
    description: str = ''
    logo_url: str = None
    python_versions: list[str] = None
    image: str = 'jupyter/minimal-notebook'

    def load_from_dict(self, data_dict):
        """Load attributes from a dictionary."""
        for key in data_dict:
            if hasattr(self, key):
                setattr(self, key, data_dict[key])


@dataclass
class MultiForm:
    """Dataclass for storing default details and list of profiles."""
    logo_url_default: str = 'https://img.eqe-lab.com/jupyter.svg'
    python_versions_default: list[str] = field(default_factory=list)
    data: list[Profile] = field(default_factory=list)

    def __iter__(self):
        for item in self.data:
            if item.logo_url is None:
                item.logo_url = self.logo_url_default
            if item.python_versions is None or not item.python_versions:
                item.python_versions = self.python_versions_default
            yield item

    def load_from_dict(self, data_dict):
        """Load attributes from a dictionary."""
        for key in data_dict:
            if hasattr(self, key):
                if key == 'data':
                    for item in data_dict[key]:
                        profile = Profile()
                        profile.load_from_dict(item)
                        self.data.append(profile)
                else:
                    setattr(self, key, data_dict[key])

# # https://github.com/manics/zero-to-jupyterhub-k8s-examples/tree/main/ldap-singleuser
class MyDockerSpawner(DockerSpawner):
    # ad_user = None
    pass
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.ad_user = None
    # def config_user(self,username:str, ad_user=None):
    #     if ad_user is None:
    #         return
    #     if username == 'chentao':
    #         userinfo=ad_user.user_check(username)
    #         self.environment['NB_UID'] = userinfo['uid']
    #         self.environment['NB_GID'] = userinfo['uid']
    #         self.environment['NB_USER'] = userinfo['username']
    #         self.environment["GIT_AUTHOR_NAME"] = userinfo["cn"]
    #         self.environment["GIT_COMMITTER_NAME"] = userinfo["cn"]
    #         self.environment["GIT_AUTHOR_EMAIL"] = userinfo["mail"]
    #         self.environment["GIT_COMMITTER_EMAIL"] = userinfo["mail"]
# class MyDockerSpawner(DockerSpawner):
#     """Custom Docker Spawner."""
#     collab_arg = '--LabApp.collaborative=True'

#     async def start(self):
#         profile = self.user_options.get('profile', 'default')
#         enable_collab = self.user_options.get(f'profile-option-{profile}-collab', 'false') == 'true'

#         self.image = f"{profile}"
#         # Retrieve the Docker image from the selected profile and set it
#         self.image = next((env.image for env in envs if env.name == profile), 'default-image')

#         if enable_collab and self.collab_arg not in self.extra_create_kwargs.get('command', []):
#             self.extra_create_kwargs.setdefault('command', []).append(self.collab_arg)

#         return await super().start()

#     @classmethod
#     def generate_form(cls, form: Profile) -> str:
#         """Generate HTML form for a single profile."""
#         form_html = f"""
#         <label for="profile-item-{form.name}" class="profile target">
#             <div class="radio">
#                 <input type="radio" name="profile" id="profile-item-{form.name}" value="{form.name}">
#             </div>
#             <div>
#                 <h3><img width="100" height="100" src="{form.logo_url}"> {form.name}</h3>
#                 <p>{form.description}</p>
#                 <div>
#                     <div class="option">
#                         <label for="profile-option-{form.name}-image">Python Version</label>
#                         <select name="profile-option-{form.name}-image" class="form-control">"""
#         for version in form.python_versions:
#             form_html += f'<option value="{version}">{version}</option>'
#         form_html += f"""
#                     </select>
#                 </div>
#                 <div class="option">
#                     <input type="checkbox" name="profile-option-{form.name}-collab" id="profile-option-{form.name}-collab" value="true">
#                     <label for="profile-optionSorry for the interruption. Please find the completed version below:

# ```python
#     {form.name}-collab">Enable collab</label>
#                 </div>
#             </div>
#         </label>
#         """
#         return form_html

#     @classmethod
#     def generate_form_multi(cls, multi_form: MultiForm) -> str:
#         """Generate HTML form for multiple profiles."""
#         form_html = ''
#         for form in multi_form:
#             form_html += cls.generate_form(form)
#         return form_html
    
#     @classmethod
#     def set_options_form(cls, multi_form: MultiForm):
#         """Set options_form attribute with generated form."""
#         cls.options_form = cls.generate_form_multi(multi_form)