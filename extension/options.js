const DEFAULT_WHITELISTED_URL_REGEXPS = [
  'abcnews.go.com\/.+',
  'arstechnica.com\/.+',
  'bbc.co.uk\/.+',
  'bbc.com\/.+',
  'business-standard.com\/.+',
  'cnn.com\/.+',
  'economist.com\/.+',
  'guardian.co.uk\/.+',
  'theguardian.com\/.+',
  'hollywoodreporter.com\/.+',
  'huffingtonpost.com\/.+',
  'irishtimes.com\/.+',
  'independent.co.uk\/.+',
  'npr.org\/.+',
  'newsweek.com\/.+',
  'nytimes.com\/.+',
  'politico.com\/.+',
  'rollingstone.com\/.+',
  'spiegel.de\/.+',
  'time.com\/.+',
  'theatlantic.com\/.+',
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
