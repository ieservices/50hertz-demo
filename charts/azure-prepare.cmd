az provider register --namespace Microsoft.ContainerService
az provider show --namespace Microsoft.ContainerService --query "registrationState" -o tsv

az aks create --resource-group Meine50hertzResourceGroup --name MeinAKSCluster --node-count 1 --enable-addons monitoring --generate-ssh-keys
az aks get-credentials --resource-group Meine50hertzResourceGroup --name MeinAKSCluster
