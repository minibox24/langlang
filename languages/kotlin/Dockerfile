# Some several tips by @aroxu

FROM adoptopenjdk/openjdk8:debian-slim
RUN apt update -y && apt install bash -y && \
    apt install wget zip unzip -y && \
    cd /usr/lib && \
    wget -q https://github.com/JetBrains/kotlin/releases/download/v1.5.21/kotlin-compiler-1.5.21.zip && \
    unzip kotlin-compiler-*.zip && \
    rm kotlin-compiler-*.zip && \
    rm -f kotlinc/bin/*.bat
ENV PATH $PATH:/usr/lib/kotlinc/bin
COPY compile.sh run.sh /