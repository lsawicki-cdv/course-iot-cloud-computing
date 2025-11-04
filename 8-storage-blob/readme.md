## Azure Blob Storage

1. Issue the following commands in **the Azure Cloud Shell (Bash)**
   1. Set the terminal environmental variables
   ```bash
      RESOURCE_GROUP_NAME="myResourceGroupFrontend"
   ```
   ```bash
      STORAGE_ACCOUNT_NAME="mystorageaccountfrontend"
   ```
   ```bash
      LOCATION="uksouth"
   ```
   2. Create a resource group using the terminal environmental variables
   ```bash
      az group create --name $RESOURCE_GROUP_NAME --location $LOCATION
   ```
   3. Create a storage account
   ```bash
      az storage account create --name $STORAGE_ACCOUNT_NAME --location $LOCATION --resource-group $RESOURCE_GROUP_NAME --sku Standard_LRS
   ```
   4. Enable static website hosting on the storage account with names for index.html and error HTML document
   ```bash
      az storage blob service-properties update --account-name $STORAGE_ACCOUNT_NAME --static-website --index-document index.html --404-document error.html
   ```
   5. Create directory `website` and go there
   ```bash
      mkdir website && cd website
   ```
   6. Create file for `index.html` in `website` directory
   ```bash
      nano index.html
   ```
   7. Copy the following content to `index.html`
   ```bash
   <!DOCTYPE html>
   <html>
      <body>
         <h1>Hello World!</h1>
      </body>
   </html>
   ```
   8. Create file for `error.html` in `website` directory
   ```bash
      nano error.html
   ```
   9. Copy the following content to `error.html`
   ```bash
   <!DOCTYPE html>
   <html>
      <body>
         <h1>ERROR</h1>
      </body>
   </html>
   ```
   10. Upload files to the `$web` container from `website` directory
   ```bash
      az storage blob upload-batch --destination \$web --source ./website --account-name $STORAGE_ACCOUNT_NAME
   ```
   11. Get the static website URL
   ```bash
      az storage account show --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --query "primaryEndpoints.web" --output tsv
   ```
2. Proof that the website is visible
3. Delete the `index.html` file from the blob storage
4. Check the website if the `error.html` is visible
5. Delete resource group