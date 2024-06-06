I use AD to manange the users, and use TrueNAS offer SMB/NFS share. Keycloak as my oidc IDP.

# My Setup
* Jupyterhub as a docker run on the server(name:code)
* server mount users' home at `/home/users/`
* jupyterhub will mount users' home automaticaly base the username and information from keycloak and AD.
* make sure the uid in contaniner is right


# how to use
* git and build by your self. change the config file [./config](./config) and run `docker compose up -d`

## need to do
* update the `config.yml`
* update `jupyterhub_config.py`