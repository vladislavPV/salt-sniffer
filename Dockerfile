FROM centos

##################Salt install###################################
RUN yum install -y https://repo.saltstack.com/yum/redhat/salt-repo-latest-2.el7.noarch.rpm
RUN yum install -y epel-release
RUN yum update -y
RUN yum install -y \
  file \
  htop \
  iproute \
  less \
  lsof \
  nano \
  net-tools \
  python-augeas \
  python2-pip \
  salt-master \
  salt-minion \
  screen \
  vim


RUN echo "auto_accept: True" >/etc/salt/master.d/autoaccept.conf \
  && echo "master: localhost" >/etc/salt/minion.d/master.conf \
  && echo "test-minion.system" >/etc/salt/minion_id

RUN   echo '#!/usr/bin/env bash' > /bin/entrypoint.sh \
  && echo 'set -o errexit' >> /bin/entrypoint.sh \
  && echo 'set -o pipefail' >> /bin/entrypoint.sh \
  && echo 'set -o nounset' >> /bin/entrypoint.sh \
  && echo 'salt-master -d' >> /bin/entrypoint.sh \
  && echo 'salt-minion -d' >> /bin/entrypoint.sh \
  && echo 'sleep 5' >> /bin/entrypoint.sh \
  && echo 'source /app/local_env' >> /bin/entrypoint.sh \
  && echo 'exec /bin/bash' >> /bin/entrypoint.sh \
  && cat /bin/entrypoint.sh \
  && chmod 777 /bin/entrypoint.sh

RUN pip install slacker

WORKDIR /app