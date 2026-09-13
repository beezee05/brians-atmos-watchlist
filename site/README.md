# Clarke's Creations — Website

A simple static website for Clarke's Creations, Caroline Clarke's handmade &
personalized gifts business (wind spinners, coffee mugs, t-shirts, slates).

## Structure

```
site/
  index.html      Page content
  css/style.css   Styling
  js/main.js      Mobile nav + contact form behavior
```

No build step or dependencies — plain HTML/CSS/JS.

## Preview locally

Open `site/index.html` directly in a browser, or serve it:

```
cd site
python3 -m http.server 8000
```

Then visit http://localhost:8000

## Things to update before launch

- Replace the placeholder email (`caroline@example.com`) in `index.html` and
  `js/main.js` with Caroline's real email.
- Add real social links (Instagram/Facebook) in the header/footer/contact
  section — currently `#` placeholders.
- Swap Caroline's bio in the "About" section for her real story, and add a
  photo if she'd like one.
- Replace the drawn product icons with real photos of finished pieces once
  available.
- The contact form currently opens the visitor's email client pre-filled
  with their message (no backend/server required). If you'd rather collect
  submissions directly (e.g. via Formspree, Netlify Forms, or a real
  backend), swap out the JS in `js/main.js`.

## Deploying

A GitHub Pages workflow (`.github/workflows/deploy-site.yml`) publishes this
folder automatically on pushes to `main`. Enable it once by going to the
repo's **Settings → Pages** and setting the source to **GitHub Actions**.
