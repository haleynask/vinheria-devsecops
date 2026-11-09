FROM jenkins/jenkins:lts-jdk17
USER root
# Python para compilar e testar os serviços durante o pipeline
RUN apt-get update && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
USER jenkins
