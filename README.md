# reapr.com.br

Source of [reapr.com.br](https://reapr.com.br), the engineering lab of Eduardo Castilho.

The site is also case 01 of the lab: a small static site run like a production service. See [This site, run like production](https://reapr.com.br/work/this-site/).

## Stack

- `build.py`: a small static site generator in Python (Markdown + Jinja2).
- GitHub Actions builds and deploys every push to `main` to GitHub Pages.
- No JavaScript. A Content-Security-Policy blocks scripts and external resources. Fonts are self-hosted.

## Run locally

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
make serve        # builds with drafts and serves on http://127.0.0.1:8000
```

## Layout

```
content/work/      cases (Problem → Approach → Result)
content/writing/   post-mortems and notes
content/pages/     about
templates/         Jinja2 templates
static/            CSS, fonts (SIL OFL), icons
site.yaml          site settings and feature flags
```

Files starting with `_` are templates and are not published. `draft: true` hides a page from the site, but not from this repository.

## Fonts

Space Grotesk, Inter and JetBrains Mono, self-hosted under the SIL Open Font License. Licenses in `static/fonts/`.
