const URL_REGEXS = [
    /abcnews.go.com\/.+/i,
    /arstechnica.com\/.+/i,
    /bbc.co.uk\/.+/i,
    /bbc.com\/.+/i,
    /business-standard.com\/.+/i,
    /cnn.com\/.+/i,
    /economist.com\/.+/i,
    /guardian.co.uk\/.+/i,
    /theguardian.com\/.+/i,
    /hollywoodreporter.com\/.+/i,
    /huffingtonpost.com\/.+/i,
    /irishtimes.com\/.+/i,
    /independent.co.uk\/.+/i,
    /npr.org\/.+/i,
    /newsweek.com\/.+/i,
    /nytimes.com\/.+/i,
    /politico.com\/.+/i,
    /rollingstone.com\/.+/i,
    /spiegel.de\/.+/i,
    /time.com\/.+/i,
    /theatlantic.com\/.+/i,
    /variety.com\/.+/i,
    /washingtonpost.com\/.+/i,
    /wired.com\/.+/i,
    /wsj.com\/.+/i,
]

const SIMILARITY_URL = 'https://tools.wmflabs.org/similarity/search';

let SuggestionsCache = new (function() {
  const MAX_CACHE_SIZE = 10;

  let cache = [];

  this.get = key => {
    for (let i = 0; i < cache.length; i++) {
      let entry = cache[i];
      if (entry.key === key) {
        return entry.value;
      }
    }
    return undefined;
  };

  this.set = (key, value) => {
    if (cache.length == MAX_CACHE_SIZE) {
      cache.shift();
    }
    cache.push({key: key, value: value});
  };
});

function getDocumentContents(callback) {
  let script = 'document.documentElement.outerHTML';
  chrome.tabs.executeScript({
    code: script
  }, (result) => { callback(result[0]); });
}

function fetchSimilarArticles(html, url, callback) {
  let formData = new FormData();
  formData.append('html', html);
  formData.append('url', url);
  let o = {method: 'POST', mode: 'cors', body: formData};
  window.fetch(SIMILARITY_URL, o).then(
    (response) => { return response.json(); }).then(callback);
}

function getSuggestionsForTab(tab, callback, options) {
  if (!tab.url) return;
  if (!options || options.canUseCache) {
    let cached = SuggestionsCache.get(tab.url);
    if (cached) {
      callback(cached);
      return;
    }
  }

  let match = false;
  for (let i = 0; i < URL_REGEXS.length; i++) {
    if (tab.url.match(URL_REGEXS[i])) {
      match = true;
    }
  }
  if (!match) return;
  getDocumentContents((html) => {
    fetchSimilarArticles(html, tab.url, suggestions => {
      SuggestionsCache.set(tab.url, suggestions);
      callback(suggestions);
    });
  });
}

chrome.tabs.onActivated.addListener((activeInfo) => {
  chrome.tabs.get(activeInfo.tabId, (tab) => {
    getSuggestionsForTab(tab, (articles) => {
      if (articles.length) {
        chrome.pageAction.show(tab.id);
      } else {
        chrome.pageAction.hide(tab.id);
      }
    });
  });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Note: this event can happen multiple times, even after the page loads,
  // and changeInfo.status can even be undefined (despite being documented
  // as only ever being either 'loading' or 'complete').
  if (changeInfo.status == 'complete') {
    getSuggestionsForTab(tab, (articles) => {
      if (articles.length) {
        chrome.pageAction.show(tab.id);
      } else {
        chrome.pageAction.hide(tab.id);
      }
    }, {canUseCache: false});
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    getSuggestionsForTab(tabs[0], sendResponse);
  });
  return true;
});
