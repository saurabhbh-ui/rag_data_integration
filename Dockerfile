FROM quay.bisinfo.org/bis/python-312:latest

USER root

RUN dnf upgrade -y libxml2-devel libxml2 zlib

RUN dnf install -y \
    unixODBC \
    unixODBC-devel \
    krb5-workstation

# Add Microsoft ODBC Driver for SQL Server repository
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --import && \
    curl https://packages.microsoft.com/config/rhel/$(rpm -E %fedora)/prod.repo > /etc/yum.repos.d/mssql-release.repo
# Update package lists again and install msodbcsql18
ENV ACCEPT_EULA=Y

RUN dnf install -y --allowerasing \
       msodbcsql18 \
       mssql-tools18 \
       unixODBC \
       unixODBC-devel
    
# Clean up
RUN dnf clean all

USER default

RUN pip install --trusted-host nexus.bisinfo.org --no-cache-dir --upgrade pip

# Installing the packages using the bis nexus repositories
COPY ./pip.conf /usr/local/pip.conf
COPY ./requirements.txt ./
COPY ./ETL ./ETL

RUN pip install --trusted-host nexus.bisinfo.org --no-cache-dir -r ./requirements.txt

# pre-download tokenizers
RUN for enc in o200k_base cl100k_base; do \
    python -c "import tiktoken; tiktoken.get_encoding('$enc')"; \
done

# Install the self-signed certificate
RUN cat $(python -m certifi) /etc/ssl/certs/*.crt > $(python -m certifi)

EXPOSE 8000
