# Deployment instructions

## How to deploy?

### Deploy the app resources

To deploy, make sure that `oc` cli is installed on your system, and [login to OCP](https://bis.ghe.com/bis/container-engineering-wiki).

Make sure your manifest is up to date.

Then run the following command to deploy the resources in the **dev** manifest
```PowerShell
oc apply -f .\manifests\manifest-dev.yaml
```
This will deploy the `Deployment`, `Service`, and `Route` in the **dev** environment.


### Deploy the secret

You will also need to manually deploy the `Secret` by creating a manifest from this template and injecting the API keys
```yaml
kind: Secret
apiVersion: v1
metadata:
  name: fsi-aicademy-secrets
  namespace: data-sandbox-dev
type: Opaque
data:
  openaiKey: <openai-api-key-in-base64>
  documentIntelligenceKey: <document-intelligence-api-key-in-base64>
```

## How to upgrade the app?

To bump the image version, you can use the utiliy script provided in this folder
```PowerShell
.\Update-Version.ps1 -filePath .\manifest-dev.yml -oldVersion "X.X.X" -newVersion "Y.Y.Y"
```
It will update the labels in `version` fields in the deployment and pods and update the version tag in the `image` field.