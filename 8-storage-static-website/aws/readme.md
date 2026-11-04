## Amazon S3 - Static Website

This is the AWS version of the [Azure Blob Storage task](../readme.md). It hosts the same two HTML pages (`index.html` and `error.html`) as a static website.

| Azure | AWS |
|-------|-----|
| Storage account | S3 bucket (the bucket name must be globally unique) |
| `$web` container | The bucket itself |
| `az storage blob service-properties update --static-website` | `aws s3 website` |
| Static website files are public automatically | Turn off Block Public Access for the bucket and add a bucket policy that allows anyone to read the files |
| `az storage blob upload-batch` | `aws s3 sync` |
| `https://<account>.z33.web.core.windows.net` (HTTPS) | `http://<bucket>.s3-website.<region>.amazonaws.com` (HTTP only) |
| Resource group | No direct equivalent - the bucket is deleted with its files |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. Amazon S3 is Free Tier eligible: 5 GB of storage, 20,000 GET and 2,000 PUT requests per month on accounts with the legacy Free Tier, or paid from your Free Tier credits on newer accounts. Two small HTML files cost a fraction of a cent. Delete the bucket at the end of the task.

### Key concepts

- **Bucket** - a container for files (objects) in S3. Its name is shared by all AWS accounts in the world, so it must be globally unique
- **Static website hosting** - S3 serves the files in the bucket as web pages, with an index document (`index.html`) and an error document (`error.html`) shown for missing pages
- **Block Public Access** - by default nothing in S3 can be public. A website must be readable by anyone, so you turn off the part that blocks public bucket policies, for this bucket only
- **Bucket policy** - a JSON document that says who may do what with the bucket. Here it allows everyone (`"Principal": "*"`) to read files (`s3:GetObject`), and nothing else
- **Website endpoint** - S3 website endpoints support only HTTP. For HTTPS, AWS puts Amazon CloudFront (a CDN) in front of the bucket, which is not part of this task

### Tested environments
Ubuntu 26.04
AWS CloudShell (Bash and PowerShell)

### Steps

1. Issue the following commands in **AWS CloudShell** (the terminal icon in the AWS Console's top bar)

   **Option A: Using Bash (recommended)**
   1. Set the terminal environmental variables. The bucket name gets random numbers, because it must be globally unique
   ```bash
      REGION="eu-west-2"  # Change to another region if needed
   ```
   ```bash
      BUCKET_NAME="mywebsite-$RANDOM$RANDOM"
   ```
   2. Create a bucket
   ```bash
      aws s3 mb s3://$BUCKET_NAME --region $REGION
   ```
   3. Enable static website hosting on the bucket with names for index.html and error HTML document
   ```bash
      aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document error.html
   ```
   4. Allow a public bucket policy for this bucket. `BlockPublicAcls` and `IgnorePublicAcls` stay on, so single files can't be made public in another way
   ```bash
      aws s3api put-public-access-block --bucket $BUCKET_NAME --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false
   ```
   5. Create a bucket policy that allows anyone to read the files in the bucket, and add it to the bucket
   ```bash
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
   ```
   ```bash
      aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://policy.json
   ```
   6. Create directory `website` and go there
   ```bash
      mkdir website && cd website
   ```
   7. Create file for `index.html` in `website` directory
   ```bash
      nano index.html
   ```
   8. Copy the following content to `index.html`, then save it (`Ctrl+O`, `Enter`) and close `nano` (`Ctrl+X`)
   ```bash
   <!DOCTYPE html>
   <html>
      <body>
         <h1>Hello World!</h1>
      </body>
   </html>
   ```
   9. Create file for `error.html` in `website` directory
   ```bash
      nano error.html
   ```
   10. Copy the following content to `error.html`, then save it and close `nano`
   ```bash
   <!DOCTYPE html>
   <html>
      <body>
         <h1>ERROR</h1>
      </body>
   </html>
   ```
   11. Upload the files from the `website` directory (the current directory) to the bucket
   ```bash
      aws s3 sync . s3://$BUCKET_NAME
   ```
   12. Get the static website URL. In some older regions (for example `us-east-1`, `us-west-2` and `eu-west-1`) the address has a dash instead of a dot: `http://<bucket>.s3-website-<region>.amazonaws.com`. You can also find it in the AWS Console: S3 → your bucket → Properties → Static website hosting
   ```bash
      echo "http://$BUCKET_NAME.s3-website.$REGION.amazonaws.com"
   ```

   **Option B: Using PowerShell**

   Start PowerShell in AWS CloudShell by typing `pwsh`.
   1. Set the terminal environmental variables (PowerShell syntax). The bucket name gets random numbers, because it must be globally unique
   ```powershell
      $REGION="eu-west-2"  # Change to another region if needed
   ```
   ```powershell
      $BUCKET_NAME="mywebsite-$(Get-Random -Maximum 999999999)"
   ```
   2. Create a bucket
   ```powershell
      aws s3 mb s3://$BUCKET_NAME --region $REGION
   ```
   3. Enable static website hosting on the bucket with names for index.html and error HTML document
   ```powershell
      aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document error.html
   ```
   4. Allow a public bucket policy for this bucket. `BlockPublicAcls` and `IgnorePublicAcls` stay on, so single files can't be made public in another way
   ```powershell
      aws s3api put-public-access-block --bucket $BUCKET_NAME --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false
   ```
   5. Create a bucket policy that allows anyone to read the files in the bucket, and add it to the bucket
   ```powershell
   @"
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
   "@ | Set-Content policy.json
   ```
   ```powershell
      aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://policy.json
   ```
   6. Create directory `website` and go there
   ```powershell
      mkdir website; cd website
   ```
   7. Create file for `index.html` in `website` directory
   ```powershell
      nano index.html
   ```
   8. Copy the following content to `index.html`, then save it (`Ctrl+O`, `Enter`) and close `nano` (`Ctrl+X`)
   ```powershell
   <!DOCTYPE html>
   <html>
      <body>
         <h1>Hello World!</h1>
      </body>
   </html>
   ```
   9. Create file for `error.html` in `website` directory
   ```powershell
      nano error.html
   ```
   10. Copy the following content to `error.html`, then save it and close `nano`
   ```powershell
   <!DOCTYPE html>
   <html>
      <body>
         <h1>ERROR</h1>
      </body>
   </html>
   ```
   11. Upload the files from the `website` directory (the current directory) to the bucket
   ```powershell
      aws s3 sync . s3://$BUCKET_NAME
   ```
   12. Get the static website URL. In some older regions (for example `us-east-1`, `us-west-2` and `eu-west-1`) the address has a dash instead of a dot: `http://<bucket>.s3-website-<region>.amazonaws.com`. You can also find it in the AWS Console: S3 → your bucket → Properties → Static website hosting
   ```powershell
      "http://$BUCKET_NAME.s3-website.$REGION.amazonaws.com"
   ```
2. Proof that the website is visible: open the URL in the browser. Note that the address starts with `http://` - S3 website endpoints don't support HTTPS
3. Delete the `index.html` file from the bucket (the same command works in Bash and PowerShell)
   ```bash
   aws s3 rm s3://$BUCKET_NAME/index.html
   ```
4. Refresh the website and check that the `error.html` page (`ERROR`) is visible. S3 shows the error document, because `index.html` no longer exists
5. Delete the bucket together with the files in it (the same command works in Bash and PowerShell)
   ```bash
   aws s3 rb s3://$BUCKET_NAME --force
   ```
