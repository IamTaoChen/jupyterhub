I use AD to manange the users, and use TrueNAS offer SMB/NFS share. Keycloak as my oidc IDP.

# My Setup
* Jupyterhub as a docker run on the server(name:code)
* server mount users' home at `/home/users/`
* jupyterhub will mount users' home automaticaly base the username and information from keycloak and AD.
* make sure the uid in contaniner is right