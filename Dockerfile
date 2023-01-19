#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
ARG spark_image_tag
FROM gitlab-registry.in2p3.fr/astrolabsoftware/fink/spark-py:${spark_image_tag}

ARG spark_uid=185
ENV spark_uid ${spark_uid}

# Reset to root to run installation tasks
USER root

RUN apt-get update && \
    apt install -y --no-install-recommends wget git apt-transport-https ca-certificates gnupg-agent apt-utils build-essential && \
    rm -rf /var/cache/apt/*

ENV PYTHONPATH ${SPARK_HOME}/python/lib/pyspark.zip:${SPARK_HOME}/python/lib/py4j-*.zip

# Specify the User that the actual main process will run as
ENV HOME /home/fink

RUN mkdir $HOME && chown ${spark_uid} $HOME

USER ${spark_uid}

ARG PYTHON_VERSION=py39_4.11.0
ENV PYTHON_VERSION=$PYTHON_VERSION

WORKDIR $HOME

# Install python
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-${PYTHON_VERSION}-Linux-x86_64.sh -O $HOME/miniconda.sh \
    && bash $HOME/miniconda.sh -b -p $HOME/miniconda

ENV PATH $HOME/miniconda/bin:$PATH

RUN $FINK_HOME/install_python_deps.sh

ENV FINK_HOME $HOME/fink-broker
ADD . $FINK_HOME/

RUN git clone -c advice.detachedHead=false --depth 1 -b "latest" --single-branch https://github.com/astrolabsoftware/fink-alert-schemas.git

ENV PYTHONPATH $FINK_HOME:$PYTHONPATH
ENV PATH $FINK_HOME/bin:$PATH
