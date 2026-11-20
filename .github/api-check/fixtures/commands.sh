#!/bin/bash
# aws s3 comment ignored
az group list \
  --output table
ACCOUNT=$(aws sts get-caller-identity --query Account)
