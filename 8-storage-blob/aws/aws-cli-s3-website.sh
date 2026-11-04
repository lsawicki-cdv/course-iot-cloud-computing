#!/bin/bash

# Variables
REGION="eu-west-2"
BUCKET_NAME="mywebsite-$RANDOM$RANDOM"

# Create a bucket
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Enable static website hosting
aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document error.html

# Allow a public bucket policy for this bucket (public ACLs stay blocked)
aws s3api put-public-access-block --bucket $BUCKET_NAME --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false

# Allow anyone to read the files in the bucket
cat > policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    }
  ]
}
EOF
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://policy.json

# Upload the files from the website directory (run from the 8-storage-blob directory)
aws s3 sync ./website s3://$BUCKET_NAME

# Get the static website URL (some older regions, e.g. us-east-1, us-west-2 and eu-west-1, use "s3-website-$REGION" instead)
echo "http://$BUCKET_NAME.s3-website.$REGION.amazonaws.com"

# Delete the bucket with its files
# aws s3 rb s3://$BUCKET_NAME --force
