---
title: This site, run like production
case: 1
status: in progress
date: 2026-11-16
summary: Treating a small static site as a production service, with checks before every deploy, probes, settings as code and an SLO.
problem: A static site with no tests, no alerts and no SLO.
approach: CI checks before deploy, uptime and certificate probes, DNS and repository settings as code, a 99.9% SLO.
stack: Python, Jinja2, GitHub Actions, GitHub Pages
repo: https://github.com/eduardocastilho/reapr.com.br
---

## Where it stands

What exists today:

- A small static site generator in Python (Markdown and Jinja2), with no JavaScript on the page.
- Every push to `main` builds and deploys the site through GitHub Actions to GitHub Pages.
- Custom domain with HTTPS enforced, and a Content-Security-Policy that blocks scripts and any external resource.
- The commit behind each deploy is shown in the footer.

## What comes next

1. **Checks before deploy.** The build fails on broken links and invalid HTML, so a bad change never reaches production.
2. **Probes and alerts.** External checks for availability and certificate expiry, with an alert when either fails.
3. **Settings as code.** DNS records and repository settings described in Terraform, where the providers allow it.
4. **An SLO.** A 99.9% availability target, the error budget it implies, and a public status panel fed only by real data.

Each step will be documented here, including what goes wrong along the way.
