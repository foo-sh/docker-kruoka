FROM docker.io/library/python:3.14.2-slim

COPY requirements.txt /usr/local/src

RUN set -eux ; \
    apt-get update ; \
    apt-get -y upgrade ; \
    rm -rf /var/lib/apt/lists/* ; \
    pip3 install --root-user-action=ignore -r /usr/local/src/requirements.txt ; \
    playwright install-deps ; \
    rm -f /usr/local/src/requirements.txt

RUN set -eux ; \ 
    find / \! \( -path /proc -prune -o -path /sys -prune \) -perm /06000 -type f -exec chmod -v a-s {} \;

RUN set -eux ; \
    mkdir -m 0755 /var/empty ; \
    groupadd kruoka ; \
    useradd -d /home/kruoka -k /dev/null -m -s /bin/false -g kruoka kruoka

COPY kruoka.py /usr/local/lib/python3.14/site-packages/

USER kruoka

RUN set -eux ; \
    playwright install firefox

EXPOSE 8000/tcp

CMD ["/usr/local/bin/gunicorn", "-b", "0.0.0.0:8000", "-w", "1", "kruoka:api"]
