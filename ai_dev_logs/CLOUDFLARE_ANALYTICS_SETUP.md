# Cloudflare Web Analytics Setup Guide

## Overview
Cloudflare Web Analytics is now enabled in the site. It will automatically track page views, visitor metrics, and user interactions without collecting personal data.

---

## 🚀 Quick Setup

### Step 1: Get Your Cloudflare Analytics Token

1. **Log in to Cloudflare Dashboard:**
   - Visit: https://dash.cloudflare.com
   - Sign in with your Cloudflare account

2. **Navigate to Web Analytics:**
   - Click **"Analytics & Logs"** in the sidebar
   - Select **"Web Analytics"**
   - Click **"Add a site"** button

3. **Configure Your Site:**
   - **Hostname:** `neurohelix.patchoutech.com` (or your domain)
   - **Automatic setup:** Yes
   - Click **"Done"**

4. **Copy Your Token:**
   - After adding the site, you'll see a JavaScript snippet
   - Look for: `data-cf-beacon='{"token": "YOUR_TOKEN_HERE"}'`
   - Copy just the token string (alphanumeric, looks like: `abc123def456...`)

---

### Step 2: Add Token to Environment Variables

**For Local Development:**

1. Create a `.env` file in the `site/` directory:
   ```bash
   cd /Users/pchouinard/Dev/NeuroHelix/site
   touch .env
   ```

2. Add your token to `.env`:
   ```env
   PUBLIC_CLOUDFLARE_ANALYTICS_TOKEN=your_actual_token_here
   ```

3. The `.env` file is already in `.gitignore` (don't commit it!)

**For Production (Cloudflare Pages):**

1. Go to your Cloudflare Pages project settings
2. Navigate to **Settings** → **Environment Variables**
3. Add a new variable:
   - **Variable name:** `PUBLIC_CLOUDFLARE_ANALYTICS_TOKEN`
   - **Value:** Your token from Step 1
   - **Environment:** Production (and Preview if desired)
4. Click **"Save"**

---

### Step 3: Verify It's Working

**Local Testing:**
```bash
cd site
pnpm dev
```

1. Open browser to `http://localhost:4321`
2. Open DevTools → Network tab
3. Look for request to `cloudflareinsights.com/beacon.min.js`
4. If you see it, analytics is enabled! ✅

**Production Testing:**
1. After deployment, visit your live site
2. Check Network tab for the beacon script
3. Wait 15-30 minutes for data to appear in Cloudflare dashboard

**View Analytics:**
- Go to: https://dash.cloudflare.com
- Navigate to: Analytics & Logs → Web Analytics
- Select your site to see metrics

---

## 📊 What Gets Tracked

Cloudflare Web Analytics tracks:
- ✅ Page views and unique visitors
- ✅ Page load performance metrics
- ✅ Top pages and referrers
- ✅ Browser and device information
- ✅ Geographic location (country-level)

**Privacy-Friendly:**
- ❌ No cookies used
- ❌ No personal data collected
- ❌ No cross-site tracking
- ✅ GDPR, CCPA, PECR compliant

---

## 🔧 Implementation Details

The analytics script is conditionally loaded in `src/layouts/BaseLayout.astro`:

```astro
const cfAnalyticsToken = import.meta.env.PUBLIC_CLOUDFLARE_ANALYTICS_TOKEN;

<!-- Only loads if token is set -->
{cfAnalyticsToken && (
  <script defer src='https://static.cloudflareinsights.com/beacon.min.js' 
          data-cf-beacon={JSON.stringify({ token: cfAnalyticsToken })}>
  </script>
)}
```

**Benefits:**
- Only loads when token is configured
- Works in development and production
- No hardcoded tokens in source code
- Safe to commit to version control

---

## 🛠️ Troubleshooting

### Script Not Loading?

**Check environment variable:**
```bash
# In your terminal
echo $PUBLIC_CLOUDFLARE_ANALYTICS_TOKEN
```

If empty, the token isn't set. Make sure:
1. `.env` file exists in `site/` directory
2. Variable starts with `PUBLIC_` (required for Astro)
3. Dev server was restarted after adding `.env`

**Check browser console:**
- Open DevTools → Console
- Look for errors related to `cloudflareinsights.com`
- If blocked, check ad blockers or privacy extensions

### Data Not Appearing in Dashboard?

- Analytics data can take **15-30 minutes** to appear initially
- Ensure you're looking at the correct site in the dashboard
- Check that your token matches the one in Cloudflare dashboard
- Local development traffic may not be tracked (only production)

### Token Syntax Issues?

**Correct format:**
```env
PUBLIC_CLOUDFLARE_ANALYTICS_TOKEN=abc123def456xyz789
```

**Incorrect formats:**
```env
# Don't include quotes
PUBLIC_CLOUDFLARE_ANALYTICS_TOKEN="abc123"

# Don't include braces
PUBLIC_CLOUDFLARE_ANALYTICS_TOKEN={"token": "abc123"}

# Don't include entire script
PUBLIC_CLOUDFLARE_ANALYTICS_TOKEN=<script>...</script>
```

---

## 🔐 Security Notes

- Environment variables prefixed with `PUBLIC_` are exposed to the client
- This is safe for Cloudflare Analytics tokens (they're meant to be public)
- Never use this pattern for API keys or sensitive credentials
- The token only tracks your specific site's analytics

---

## 📈 Custom Event Tracking

To track custom events (optional):

```javascript
// In any client-side script
if (window.cfBeacon) {
  window.cfBeacon.track('button-click', {
    label: 'hero-cta'
  });
}
```

**Pre-tracked events in the site:**
- Hero CTA clicks: `data-cf-event="hero-cta-click"`

---

## 🚫 Disabling Analytics

**Temporarily disable (local dev):**
```bash
# Remove or comment out the line in .env
# PUBLIC_CLOUDFLARE_ANALYTICS_TOKEN=...
```

**Permanently disable:**
```bash
# Delete the .env file
rm site/.env

# Remove from Cloudflare Pages environment variables
```

The script will not load if the token is not set.

---

## ✅ Checklist

- [ ] Cloudflare account created
- [ ] Site added to Web Analytics
- [ ] Token copied from dashboard
- [ ] `.env` file created with token
- [ ] Dev server restarted
- [ ] Script loads in browser Network tab
- [ ] Token added to Cloudflare Pages environment variables (production)
- [ ] Site deployed and tested

---

## 📚 Additional Resources

- [Cloudflare Web Analytics Docs](https://developers.cloudflare.com/analytics/web-analytics/)
- [Astro Environment Variables](https://docs.astro.build/en/guides/environment-variables/)
- [Cloudflare Pages Environment Variables](https://developers.cloudflare.com/pages/platform/build-configuration/#environment-variables)

---

**Last Updated:** November 7, 2025
