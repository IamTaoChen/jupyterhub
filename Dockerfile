ARG VERSION=4.0
FROM jupyterhub/jupyterhub:${VERSION}

# RUN wget https://raw.githubusercontent.com/jupyterhub/jupyterhub/0.9.3/examples/cull-idle/cull_idle_servers.py

RUN python3 -m pip install  jupyterhub-idle-culler dockerspawner \
                            oauthenticator PyYAML ldap3\
    && pip cache purge

ADD src/config/ /etc/jupyterhub/
ENV CONFIG_SCRIPT_DIR='/config'
RUN mkdir -p $CONFIG_SCRIPT_DIR && cp -r /etc/jupyterhub/* $CONFIG_SCRIPT_DIR

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/hub/api || exit 1

