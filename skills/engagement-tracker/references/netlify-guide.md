# Netlify Deployment Guide

Step-by-step guide to deploy your Engagement Intelligence dashboard to Netlify.

---

## 1. Create a Netlify Account

1. Go to [netlify.com](https://www.netlify.com)
2. Click **Sign up** and create an account (the free tier works fine)
3. Verify your email

---

## 2. Deploy Your Dashboard

Choose one of two options:

### Option A: Drag & Drop (Easiest)

1. Go to [app.netlify.com/drop](https://app.netlify.com/drop)
2. Open Finder (macOS) or File Explorer (Windows) and locate the `output/` folder that the build script generated
3. Drag the entire `output/` folder onto the Netlify drop zone on the page
4. Wait for the upload to complete
5. Netlify assigns a random URL (e.g., `https://random-name-12345.netlify.app`) -- your dashboard is now live

### Option B: Netlify CLI

For repeat deployments, the CLI is faster.

```bash
# Install the Netlify CLI (one-time)
npm install -g netlify-cli

# Log in to your Netlify account (one-time)
netlify login

# Deploy to production
netlify deploy --prod --dir=./output
```

On first deploy, the CLI will prompt you to link to an existing site or create a new one. Choose **Create & configure a new site**.

---

## 3. Custom Site Name

The default URL is a random string. To set a readable name:

1. Go to your site in the Netlify dashboard
2. Click **Site configuration** (or **Settings**)
3. Under **Domain management**, click **Options** next to the default subdomain
4. Click **Edit site name**
5. Enter your preferred name (e.g., `acme-engagement`)
6. Your site is now available at `https://acme-engagement.netlify.app`

---

## 4. Password Protection

The dashboard includes a built-in JavaScript password gate. The password is set in the client config JSON file (the `password` field).

**How it works:**
- When someone visits the dashboard URL, they see a password prompt
- They enter the password and click "Enter"
- The dashboard content is revealed
- This is client-side protection, sufficient for internal team dashboards

**For server-side authentication:**
- Upgrade to Netlify Pro plan
- Use Netlify's built-in Basic Auth (password protection at the server level)
- This prevents the HTML source from being visible to unauthorized users

---

## 5. Updating the Dashboard

When you have new engagement data (new posts, new engagers):

1. Update your CSV files with the new data
2. Re-run the build script
3. Re-deploy using either method:
   - **Drag & drop**: Go to your site in Netlify dashboard, click **Deploys**, then drag the new `output/` folder onto the deploy area
   - **CLI**: Run `netlify deploy --prod --dir=./output` again

The URL stays the same. Stakeholders can refresh the page to see updated data.

---

## 6. Custom Domain (Optional)

To use your own domain (e.g., `engagement.acme.com`):

1. Go to your site's **Domain management** settings in Netlify
2. Click **Add custom domain**
3. Enter your domain name
4. Follow Netlify's instructions to configure DNS:
   - **Option A**: Point your domain's DNS to Netlify's nameservers
   - **Option B**: Add a CNAME record pointing to your Netlify site URL
5. Netlify automatically provisions an SSL certificate (free via Let's Encrypt)

---

## 7. Sharing the Dashboard

Once deployed, share the following with stakeholders:

1. **URL**: The Netlify site URL (e.g., `https://acme-engagement.netlify.app`)
2. **Password**: The password configured in the client config file

That is all they need. The dashboard is fully self-contained with no additional setup required on the viewer's end.
