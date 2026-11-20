# Fixture

Inline `az ignored inline` is not a fence.

1. Login to the registry:

   ```bash
   aws ecr get-login-password --region r | docker login --username AWS --password-stdin x
   ```

2. Deeper fence:

      ```bash
      az cognitiveservices account list --query "[?kind=='OpenAI' && x]"
      ```

Bash with continuations:

```bash
# aws comment ignored
aws s3api create-bucket \
  --bucket b \
  --region r
if az group show --name g; then
  X=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS)
fi
aws dynamodb wait table-exists --table-name t
aws --version
aws configure
az $(touch /tmp/pwned) --help
```

PowerShell with backticks:

```powershell
az vm create `
  --name n `
  --resource-group g
```

```python
os.system("aws s3 ls --python-ignored")
```

```json
{"cmd": "az ignored json"}
```

```
az group list --output table
```
