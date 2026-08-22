Source check for multi-year CafeF sampling:

- Direct browser verification succeeded for https://cafef.vn/sitemaps/sitemaps-2021-10-1-5.xml. The sitemap returned historical CafeF URLs with 2021-10 timestamps and article locations.
- Direct browser verification succeeded for https://cafef.vn/sitemaps/sitemaps-2020-10-1-5.xml. The sitemap returned historical CafeF URLs with 2020-10 timestamps and article locations.
- The existing crawler uses the same sitemap naming convention for October 2022, so October-by-year sampling is a compatible default design for 2019--2022.
- The 2019 sitemap should be probed with the same URL pattern before the full crawl; the final pipeline should log missing/failed sitemap partitions rather than silently treating them as empty.

- Direct browser verification also succeeded for https://cafef.vn/sitemaps/sitemaps-2019-10-1-5.xml and https://cafef.vn/sitemaps/sitemaps-2022-10-1-5.xml. Both returned historical October article URLs with matching year-month timestamps.
- The October 2019, 2020, 2021, and 2022 sitemap partitions therefore appear available under one consistent URL pattern. The implementation should still validate every partition and save a manifest of counts/errors per year-month.
