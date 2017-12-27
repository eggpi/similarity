const SIMILARITY_URL = 'https://tools.wmflabs.org/similarity/search';

let SuggestionsCache = new (function() {
  const MAX_CACHE_SIZE = 10;
  const ENTRY_TTL_S = 10 * 60;

  this._cache = [];

  this._expire = () => {
    this._cache = this._cache.filter((entry) => {
      return ((new Date() - entry.date) / 1000) < ENTRY_TTL_S;
    });
  }

  this.get = key => {
    this._expire();
    for (let i = 0; i < this._cache.length; i++) {
      let entry = this._cache[i];
      if (entry.key === key) {
        return entry.value;
      }
    }
    return undefined;
  };

  this.set = (key, value) => {
    this._expire();
    if (this._cache.length == MAX_CACHE_SIZE) {
      this._cache.shift();
    }
    this._cache = this._cache.filter(entry => entry.key !== key);
    this._cache.push({key: key, value: value, date: new Date()});
  };
});

function getDocumentContents() {
  return new Promise((resolve, reject) => {
    let script = 'document.documentElement.outerHTML';
    chrome.tabs.executeScript({
      code: script
    }, (result) => { resolve(result[0]); });
  });
}

function fetchSimilarArticles(html, url) {
  let formData = new FormData();
  formData.append('html', html);
  formData.append('url', url);
  let o = {method: 'POST', mode: 'cors', body: formData};
  return window.fetch(SIMILARITY_URL, o).then(
    (response) => { return response.json() }).then(
    (response) => {
      console.log(response['debug']);
      return response['results'];
    });
}

function getSuggestionsForTab(tab, options) {
  return new Promise((resolve, reject) => {
    if (!tab.url) {
      reject('No URL!');
      return;
    }

    let whitelist = loadURLsWhitelist();
    let match = whitelist.some((w) => {
      return tab.url.match(RegExp(w));
    });
    if (!match) {
      resolve([]);
      return;
    };

    if (!options || options.canUseCache) {
      let cached = SuggestionsCache.get(tab.url);
      if (cached) {
        resolve(cached);
        return;
      }
    }

    resolve(getDocumentContents().then((html) => {
      return fetchSimilarArticles(html, tab.url);
    }).then((suggestions) => {
      SuggestionsCache.set(tab.url, suggestions);
      return suggestions;
    }));
  });
}

function getSuggestionsAndUpdateUI(tab, options) {
  getSuggestionsForTab(tab, options).then((articles) => {
    if (articles.length) {
      chrome.pageAction.show(tab.id);
    } else {
      chrome.pageAction.hide(tab.id);
    }
  }).catch((e) => {
    console.log(e);
    chrome.pageAction.hide(tab.id);
  });
}

chrome.tabs.onActivated.addListener((activeInfo) => {
  chrome.tabs.get(activeInfo.tabId, (tab) => {
    getSuggestionsAndUpdateUI(tab);
  });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Note: this event can happen multiple times, even after the page loads,
  // and changeInfo.status can even be undefined (despite being documented
  // as only ever being either 'loading' or 'complete').
  if (changeInfo.status == 'complete') {
    getSuggestionsAndUpdateUI(tab, {canUseCache: false});
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    getSuggestionsForTab(tabs[0]).then(sendResponse);
  });
  return true;
});
