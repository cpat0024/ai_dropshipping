# Troubleshooting

AliExpress can present CAPTCHAs, bot checks, and region/language redirects. Tips for the Scrapfly backend:

- Provide a valid `SCRAPFLY_KEY` and ensure your plan/quota allows JS rendering.
- Use the `--country` flag and, if needed, `--aep-cookie` to localize currency and language.
- Slow down: the scraper already adds small random delays between requests.
- Expect occasional failures; the code handles retries and logs warnings when a product fails.
- Don’t attempt to bypass CAPTCHAs or access controls.
