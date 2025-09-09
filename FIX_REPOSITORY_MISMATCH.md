# Fix Repository Mismatch Between Local and Railway

## Problem
Railway is configured to use repository `omnigapai/google_workspace_mcp` (with underscores) but the actual GitHub repository is `omnigapai/paestro-google-workspace-mcp` (with hyphens).

## Solution

### Option 1: Update Railway to Use Correct Repository (RECOMMENDED)
1. Go to Railway dashboard: https://railway.com/project/837c3d17-5faa-404b-96e2-f6c445c4c870
2. Navigate to Settings → GitHub Repository
3. Disconnect the current repository
4. Connect to the correct repository: `omnigapai/paestro-google-workspace-mcp`
5. Railway will automatically trigger a new deployment

### Option 2: Create Matching Repository on GitHub
1. Create new repository on GitHub: `omnigapai/google_workspace_mcp`
2. Push existing code to new repository:
```bash
git remote add railway-repo https://github.com/omnigapai/google_workspace_mcp.git
git push railway-repo main
```
3. Railway will automatically detect and deploy

### Option 3: Update Railway Configuration via CLI
```bash
# In the google-workspace-mcp directory
railway link
# Select the Google Workspace MCP project
railway service
# Select the service
railway variables set RAILWAY_GIT_REPO_URL=https://github.com/omnigapai/paestro-google-workspace-mcp.git
```

## Current Status
- Local repository: `https://github.com/omnigapai/paestro-google-workspace-mcp.git` ✅
- Railway expects: `omnigapai/google_workspace_mcp` ❌
- Deployment: Manual trigger works, automatic GitHub triggers fail

## After Fix
Once the repository mismatch is resolved:
1. GitHub pushes will automatically trigger Railway deployments
2. No more manual deployments needed
3. CI/CD pipeline will work correctly