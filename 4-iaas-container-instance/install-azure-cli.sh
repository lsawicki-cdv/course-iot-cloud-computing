#!/bin/bash

curl -sL https://aka.ms/InstallAzureCLIDeb | bash && rm -rf /var/lib/apt/lists/* && az extension add -n azure-iot