### 1. Add MinIO Helm repo

```bash
helm repo add minio https://charts.min.io/
helm repo update
```

### 2. Install MinIO into the cluster
```bash
helm install minio minio/minio \
  --namespace openwhisk \
  --set mode=standalone \
  --set resources.requests.memory=256Mi \
  --set persistence.enabled=false \
  --set accessKey=minio \
  --set secretKey=Benji2020!
```

MinIO will run inside Kubernetes with a persistent volume.

### 3. Expose MinIO locally

```bash
kubectl port-forward -n openwhisk deploy/minio 9000:9000
```

Login with:

```
username: minio
password: password
```


## Create bucket before first use

```bash
kubectl exec -it deploy/minio -n openwhisk -- \
  mc alias set local http://localhost:9000 minio password

kubectl exec -it deploy/minio -n openwhisk -- \
  mc mb local/results
```

---

## 🔗 Access from outside Minikube (optional)

```bash
minikube service minio -n openwhisk
```

---

## ✅ Summary

| Goal                            | Solution              |
| ------------------------------- | --------------------- |
| Store images locally            | MinIO inside Minikube |
| S3 API compatible               | Yes                   |
| Works without internet          | Yes                   |
| Accessible to OpenWhisk actions | Yes                   |
| Can persist to disk             | Yes, via PVC          |

---

## ❓ Next: What do you want?

```
1) full ready-to-use postprocess action code
2) MinIO setup script + wskdeploy YAML
3) full workflow: preprocess → detect → postprocess → MinIO
4) return both JSON + URL
```

Reply with **1, 2, 3 or 4**.
