const DEFAULT_WHITELISTED_URL_REGEXPS = [
  'abcnews.go.com\/.+',
  'arstechnica.com\/.+',
  'bbc.co.uk\/.+',
  'bbc.com\/.+',
  'business-standard.com\/.+',
  'cnn.com\/.+',
  'economist.com\/.+',
  'forbes.com\/.+',
  'guardian.co.uk\/.+',
  'hollywoodreporter.com\/.+',
  'huffingtonpost.com\/.+',
  'independent.co.uk\/.+',
  'irishtimes.com\/.+',
  'newsweek.com\/.+',
  'newyorker.com\/.+',
  'npr.org\/.+',
  'nytimes.com\/.+',
  'politico.com\/.+',
  'rollingstone.com\/.+',
  'spiegel.de\/.+',
  'theatlantic.com\/.+',
  'theguardian.com\/.+',
  'time.com\/.+',
  'variety.com\/.+',
  'washingtonpost.com\/.+',
  'wired.com\/.+',
  'wsj.com\/.+',
];

function saveURLsWhitelist(whitelist) {
  localStorage.setItem('urls-whitelist', JSON.stringify(whitelist));
}

function loadURLsWhitelist() {
  let whitelist = localStorage.getItem('urls-whitelist');
  if (whitelist) {
    return JSON.parse(whitelist);
  }
  return DEFAULT_WHITELISTED_URL_REGEXPS;
}
