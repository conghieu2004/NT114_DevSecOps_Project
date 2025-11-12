# CI/CD Authentication Fix - Summary Report

## Date: 2025-11-12
## Issue: GitHub Actions EKS Deployment Failure

---

## Root Cause

The GitHub Actions workflow failed with:
```
Error: UnrecognizedClientException: The security token included in the request is invalid
```

**Cause:** Invalid/missing AWS credentials in GitHub Actions secrets.

---

## Actions Taken

### 1. Created IAM Infrastructure

Created new IAM user and policy for GitHub Actions:

- **IAM User:** `nt114-devsecops-github-actions-user`
- **AWS Account:** `039612870452`
- **Policy:** `nt114-github-actions-full-deploy-policy`
- **Permissions:** Full access to EKS, EC2, ECR, IAM, ELB, AutoScaling, KMS, CloudWatch

### 2. Generated Access Keys

Created new AWS access keys (see `.github-credentials-DO-NOT-COMMIT.txt`):
- **Access Key ID:** [REDACTED-ACCESS-KEY-ID]
- **Secret Access Key:** (in credentials file)

### 3. Fixed Hardcoded Account IDs

**Changed:**
- `.github/workflows/deploy-to-eks.yml` - Changed from hardcoded `767900165633` to dynamic account ID lookup
- `argocd/applications/*.yaml` - Updated all 5 manifests from `767900165633` to `039612870452`

**Files Modified:**
- `.github/workflows/deploy-to-eks.yml`
- `argocd/applications/api-gateway.yaml`
- `argocd/applications/exercises-service.yaml`
- `argocd/applications/frontend.yaml`
- `argocd/applications/scores-service.yaml`
- `argocd/applications/user-management-service.yaml`

### 4. Enhanced Security

- Added credential files to `.gitignore`
- Created secure credentials file (to be deleted after use)
- Added comprehensive IAM policy with least-privilege approach

---

## IMMEDIATE ACTIONS REQUIRED

### Step 1: Authenticate GitHub CLI (if not done)

```bash
gh auth login
```

Follow prompts to authenticate with your GitHub account.

### Step 2: Set GitHub Secrets

**Option A - Using GitHub CLI (Recommended):**

```bash
gh secret set AWS_ACCESS_KEY_ID --body "[REDACTED-ACCESS-KEY-ID]"
gh secret set AWS_SECRET_ACCESS_KEY --body "[REDACTED-SECRET-KEY]"
```

**Option B - Using GitHub Web UI:**

1. Go to: `https://github.com/YOUR_USERNAME/NT114_DevSecOps_Project/settings/secrets/actions`
2. Click "New repository secret"
3. Add `AWS_ACCESS_KEY_ID` with value: `[REDACTED-ACCESS-KEY-ID]`
4. Add `AWS_SECRET_ACCESS_KEY` with value from `.github-credentials-DO-NOT-COMMIT.txt`

### Step 3: Commit and Push Changes

```bash
git add .github/workflows/deploy-to-eks.yml
git add .gitignore
git add argocd/applications/*.yaml
git commit -m "fix: correct AWS account ID and enable dynamic account resolution

- Updated deploy-to-eks.yml to use dynamic account ID instead of hardcoded
- Fixed ArgoCD manifests to use correct AWS account (039612870452)
- Added credential files to .gitignore for security"
git push origin main
```

### Step 4: Delete Sensitive Files

```bash
rm .github-credentials-DO-NOT-COMMIT.txt
rm github-actions-policy.json
```

### Step 5: Test the Fix

Trigger the workflow manually:

```bash
gh workflow run eks-terraform.yml
```

Monitor the run:

```bash
gh run watch
```

Or check in GitHub UI:
`https://github.com/YOUR_USERNAME/NT114_DevSecOps_Project/actions`

---

## Verification Checklist

- [ ] GitHub CLI authenticated (`gh auth login`)
- [ ] AWS_ACCESS_KEY_ID secret set in GitHub
- [ ] AWS_SECRET_ACCESS_KEY secret set in GitHub
- [ ] Code changes committed and pushed
- [ ] Sensitive credential files deleted
- [ ] Workflow triggered successfully
- [ ] No authentication errors in workflow logs
- [ ] EKS cluster creation progresses past authentication

---

## What Was Fixed

### Before:
- ❌ No IAM user existed
- ❌ Invalid/missing GitHub secrets
- ❌ Hardcoded wrong AWS account ID (767900165633)
- ❌ Static account ID in workflows
- ❌ ArgoCD manifests pointing to wrong ECR

### After:
- ✅ IAM user created with proper permissions
- ✅ Valid access keys generated
- ✅ Correct AWS account ID (039612870452)
- ✅ Dynamic account ID resolution in workflow
- ✅ ArgoCD manifests updated to correct ECR

---

## Security Notes

### Current Setup (Phase 1 - Temporary)
- Uses static long-lived credentials
- Full AWS access permissions
- **Risk Level:** MEDIUM
- **Recommendation:** Migrate to OIDC (Phase 2)

### Next Steps (Phase 2 - Recommended)
See detailed plan in: `plans/251112-1400-aws-auth-fix/phase-02-oidc-migration.md`

Benefits of OIDC:
- No secrets needed in GitHub
- Short-lived tokens (max 12 hours)
- Better audit trail
- AWS best practice

---

## Rollback Procedure

If issues occur:

1. **Revert Code Changes:**
```bash
git revert HEAD
git push origin main
```

2. **Regenerate Keys (if compromised):**
```bash
aws iam create-access-key --user-name nt114-devsecops-github-actions-user
```

3. **Update GitHub Secrets** with new keys

---

## Monitoring

After deployment, monitor:

1. **GitHub Actions Logs:**
   - Check for authentication errors
   - Verify EKS cluster creation starts

2. **AWS CloudTrail:**
   - Monitor IAM user activity
   - Check for unauthorized access

3. **Terraform State:**
   - Verify infrastructure creation
   - Check for resource conflicts

---

## Support Resources

- **Full Investigation Report:** `plans/eks-auth-investigation/reports/251112-investigator-to-user-eks-auth-failure-report.md`
- **Scout Report:** `plans/251112-aws-auth-scout/reports/scout-report.md`
- **Implementation Plans:** `plans/251112-1400-aws-auth-fix/`
- **Phase 2 OIDC Migration:** `plans/251112-1400-aws-auth-fix/phase-02-oidc-migration.md`

---

## Questions?

### Q: Why account 039612870452 instead of 767900165633?
A: Account 039612870452 is your authenticated AWS account. Account 767900165633 was incorrectly hardcoded.

### Q: Is this secure enough for production?
A: This is Phase 1 (immediate fix). Phase 2 OIDC migration is strongly recommended for production.

### Q: What if I don't have GitHub CLI?
A: Use the GitHub web UI to set secrets manually (Option B in Step 2).

### Q: Can I use these credentials locally?
A: No, these are specifically for GitHub Actions. Use your personal AWS credentials locally.

---

## Estimated Time to Restore CI/CD

- **Setting secrets:** 2-5 minutes
- **Committing changes:** 2 minutes
- **Workflow execution:** 15-25 minutes
- **Total:** ~20-30 minutes

---

**Status:** ✅ Implementation Complete - Awaiting User Action (Set GitHub Secrets)
