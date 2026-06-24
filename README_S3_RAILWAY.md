# 📦 Configuration S3 Railway Bucket pour Vidéos Publicitaires

## 🎯 Problème résolu

Auparavant, les vidéos étaient stockées localement dans `static/uploads/publicites/`, ce qui provoquait leur disparition à chaque déploiement sur Railway.

**Solution** : Migration vers le Railway Object Storage (compatible S3) pour un stockage persistant.

---

## ⚙️ Variables d'environnement à configurer dans Railway

Ajoutez les variables suivantes dans votre projet Railway :

| Variable | Description | Exemple |
|----------|-------------|---------|
| `S3_ENDPOINT_URL` | URL du endpoint S3 Railway | `https://s3.railwayinternal.com` |
| `S3_BUCKET_NAME` | Nom du bucket Railway | `nova-trade-videos` |
| `AWS_ACCESS_KEY_ID` | Clé d'accès AWS/Railway | `RWXXXXXXXXXXXXXXXXXXXX` |
| `AWS_SECRET_ACCESS_KEY` | Clé secrète AWS/Railway | `XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` |

### Comment obtenir ces valeurs depuis Railway :

1. Allez sur votre projet Railway
2. Créez un **Object Storage** (Railway S3)
3. Dans les paramètres du bucket, récupérez :
   - Endpoint URL
   - Bucket Name
   - Access Key ID
   - Secret Access Key

---

## 🔄 Modifications apportées au code

### 1. `requirements.txt`
Ajout de `boto3==1.34.0` pour les opérations S3.

### 2. `app.py`
- Suppression de `UPLOAD_FOLDER_PUBLICITES` (stockage local)
- Ajout des fonctions S3 :
  - `get_s3_client()` - Crée le client boto3
  - `upload_to_s3()` - Upload les vidéos vers le bucket
- Modification de `api_creer_publicite()` pour utiliser S3

---

## 📝 Comportement après migration

### Upload d'une vidéo
1. La vidéo est uploadée directement vers le bucket S3 Railway
2. Une URL publique est générée (ex: `https://s3.railwayinternal.com/nova-trade-videos/publicites/pub_abc123.mp4`)
3. Cette URL est stockée dans la base de données (`publicite.video_url`)
4. Le fichier reste accessible même après redéploiement

### Lecture d'une vidéo
- Le template `publicite.html` utilise directement l'URL S3 stockée en base
- Pas de changement pour l'utilisateur final

---

## ✅ Vérification

Après configuration des variables d'environnement :

1. **Redéployez l'application** sur Railway
2. **Testez l'upload** d'une vidéo publicitaire
3. **Vérifiez** que la vidéo est lisible
4. **Redéployez** à nouveau → la vidéo doit toujours être accessible

---

## 🛠️ Dépannage

### Erreur "Configuration S3 incomplète"
→ Vérifiez que toutes les variables d'environnement sont définies dans Railway.

### Erreur "Identifiants S3 invalides"
→ Vérifiez `AWS_ACCESS_KEY_ID` et `AWS_SECRET_ACCESS_KEY`.

### Vidéo non lisible après upload
→ Vérifiez que le bucket a les permissions ACL `public-read` activées.

---

## 📚 Liens utiles

- [Railway Object Storage Documentation](https://docs.railway.app/guides/object-storage)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)