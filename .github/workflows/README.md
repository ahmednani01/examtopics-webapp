# GitHub Actions CI/CD Setup

## GitHub Secrets Required

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Value |
|------------|-------|
| `VPS_HOST` | `207.180.243.180` |
| `VPS_USER` | `brewuser` |
| `VPS_PASSWORD` | Your VPS password |

## How It Works

1. Push to `main` branch
2. GitHub Actions triggers the workflow
3. SSH into your VPS
4. Pull latest code
5. Rebuild and restart containers with `docker-compose`

## Setup VPS Repository

On your VPS, make sure the examtopics repo is set up:

```bash
# SSH into your VPS
ssh brewuser@207.180.243.180

# Navigate to your project directory
cd /home/brewuser/examtopics

# Check if it's a git repo
git remote -v

# If not, clone your repo:
git clone <your-github-repo-url> examtopics
cd examtopics
docker-compose up -d
```

## First Deployment

After setting up secrets, trigger a deploy:

```bash
git add .
git commit -m "Add CI/CD"
git push origin main
```

This will automatically deploy to your VPS.
