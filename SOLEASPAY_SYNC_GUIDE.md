# 🔄 Guide de Synchronisation SoleasPay

## 📋 Problème résolu

**Avant** : Les retraits restaient bloqués sur "En attente" même après que SoleasPay ait envoyé l'argent.

**Après** : Synchronisation automatique des statuts via webhook.

## 🔧 Comment ça marche ?

### 1. Flux de retrait avec SoleasPay

```
1. Utilisateur demande un retrait
   ↓
2. Notre app → API SoleasPay (POST /api/action/account/withdraw)
   ↓
3. Réponse SoleasPay : {"success": true, "status": "PROCESSING", "reference": "MLS109P"}
   ↓
4. Notre app enregistre le retrait avec statut "en_attente" + reference_soleaspay="MLS109P"
   ↓
5. SoleasPay traite le paiement (peut prendre quelques minutes)
   ↓
6. SoleasPay → Notre webhook (POST /api/webhook/soleaspay)
   ↓
7. Notre webhook met à jour le statut : "en_attente" → "successful"
   ↓
8. L'utilisateur voit le statut mis à jour dans "Mes retraits"
```

### 2. Configuration requise

#### A. Exécuter le script SQL

```bash
# Se connecter à la base de données (Railway ou local)
psql $DATABASE_URL -f add_retrait_soleaspay_columns.sql
```

Ce script ajoute :
- `reference_soleaspay` (VARCHAR 100) : Référence du retrait chez SoleasPay
- `last_sync` (TIMESTAMP) : Date de dernière synchronisation

#### B. Configurer le webhook SoleasPay

Dans votre tableau de bord SoleasPay, configurez :

- **URL du webhook** : `https://votre-domaine.com/api/webhook/soleaspay`
- **Clé secrète** (x-private-key) : `b42ed39b9e0db71db4556a2dfe1b1ad00dcce656fd4dba033f1947f913f1908bc817588c2edb32d92533a1d162e57ad4b1f7299f39695c5671c3ef07baa6f22a`

⚠️ **Important** : Cette clé doit correspondre exactement à `SOLEAS_WEBHOOK_SECRET` dans `app.py`.

#### C. Redéployer l'application

```bash
cd e
git push
# Railway va redéployer automatiquement
```

## 🧪 Tester la solution

### 1. Faire un retrait test

1. Connectez-vous à votre compte
2. Allez sur `/retrait`
3. Remplissez le formulaire (montant, numéro, service)
4. Entrez votre code PIN
5. Validez

### 2. Vérifier les logs

Après le retrait, consultez les logs Railway :

```bash
# Voir les logs en temps réel
railway logs

# Ou filtrer par retrait
railway logs | grep "RETRAIT"
```

Vous devriez voir :
```
[SOLEASPAY] Envoi retrait: service_id=1, wallet=677347922, montant=5000
[SOLEASPAY] Status HTTP: 200
[SOLEASPAY] Réponse: {'success': True, 'status': 'PROCESSING', ...}
[RETRAIT] User 123 - Retrait enregistré avec succès: montant=5000
```

### 3. Attendre le webhook

Quand SoleasPay aura traité le paiement (généralement quelques minutes), vous recevrez un webhook :

```
[WEBHOOK RETRAIT] Retrait ID 456 - Statut reçu: SUCCESS
[WEBHOOK RETRAIT] Retrait 456 marqué comme SUCCESSFUL ✅
```

### 4. Vérifier dans "Mes retraits"

Allez sur `/mes-retraits` et vérifiez que le statut est passé à "Succès" ou "successful".

## 🔍 Debugging

### Le webhook ne fonctionne pas ?

1. **Vérifier l'URL du webhook** :
   - L'URL doit être accessible depuis internet
   - Testez avec : `curl -X POST https://votre-domaine.com/api/webhook/soleaspay`

2. **Vérifier la clé secrète** :
   - La clé dans SoleasPay doit correspondre à `SOLEAS_WEBHOOK_SECRET` dans `app.py`

3. **Vérifier les logs** :
   ```bash
   railway logs | grep "WEBHOOK"
   ```

4. **Tester manuellement** :
   ```bash
   curl -X POST https://votre-domaine.com/api/webhook/soleaspay \
     -H "Content-Type: application/json" \
     -H "x-private-key: b42ed39b9e0db71db4556a2dfe1b1ad00dcce656fd4dba033f1947f913f1908bc817588c2edb32d92533a1d162e57ad4b1f7299f39695c5671c3ef07baa6f22a" \
     -d '{"success": true, "status": "SUCCESS", "data": {"external_reference": "NOVA-W-123", "reference": "MLS109P", "amount": 5000}}'
   ```

### Les colonnes n'existent pas ?

Exécutez le script SQL :
```bash
psql $DATABASE_URL -f add_retrait_soleaspay_columns.sql
```

Vérifiez que les colonnes existent :
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'retrait' 
  AND column_name IN ('reference_soleaspay', 'last_sync');
```

## 📊 Statuts possibles

| Statut SoleasPay | Statut dans l'app | Signification |
|-----------------|-------------------|---------------|
| PROCESSING | en_attente | Retrait en cours de traitement |
| SUCCESS | successful | Retrait réussi ✅ |
| COMPLETED | successful | Retrait réussi ✅ |
| APPROVED | successful | Retrait réussi ✅ |
| FAILED | failed | Échec du retrait ❌ |
| REJECTED | refused | Retrait refusé ❌ |
| CANCELLED | cancelled | Retrait annulé ⚠️ |

## 🎯 Résultat attendu

Après ces modifications :

1. ✅ Les retraits sont créés avec statut "en_attente"
2. ✅ La référence SoleasPay est stockée (`reference_soleaspay`)
3. ✅ Quand SoleasPay confirme, le webhook met à jour le statut
4. ✅ L'historique des retraits affiche le **vrai statut**
5. ✅ Plus de "En attente" qui reste bloqué indéfiniment

## 🆘 Support

Si vous rencontrez des problèmes :

1. Vérifiez les logs Railway
2. Testez le webhook manuellement avec curl
3. Vérifiez que les colonnes existent dans la BDD
4. Contactez-moi avec les logs complets

---

**Dernière mise à jour** : 26/06/2026
**Version** : 1.0